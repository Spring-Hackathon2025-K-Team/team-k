
  document.addEventListener('DOMContentLoaded', function() {
    // 現在の閲覧しているチャンネルをハイライト表示する（サイドバー）
    const currentUrl = window.location.pathname;
    const channelLinks = document.querySelectorAll('.channel-link');
    
    channelLinks.forEach(link => {
      if (link.getAttribute('href') === currentUrl) {
        link.parentElement.classList.add('active');
      }
    });
  });



// <!-- WebSocket用JavaScript -->

  document.addEventListener('DOMContentLoaded', function() {

    const chatContainer = document.querySelector('.chat-container');
    const currentChannelId = chatContainer ? parseInt(chatContainer.dataset.channelId) : null;
    const currentUserId = chatContainer ? chatContainer.dataset.userId : null;

      // Socket.IOクライアントを初期化して作る
      const socket = io();
      
      // 現在のチャンネルIDを取得、チャンネルが選択されていない場合はnull
      const currentChannelId = {% if current_channel %}{{ current_channel.id }}{% else %}null{% endif %};
      const currentUserId = '{{ uid }}';
      
      // チャンネルに参加
      if (currentChannelId) {
        //バックへのエンドポイント「join_channel」でcurrentChannelIdをchannel_idとして送信
          socket.emit('join_channel', {channel_id: currentChannelId});
      }

      //サーバーから新しいメッセージが届いたときにチャット画面に追加して画面を一番下までスクロールする機能
      // エンドポイント「new_message」で指定したデータを受け取り、コールバック関数の引数(data)に格納
      socket.on('new_message', function(data) {
          addMessageToChat(data);
          scrollToBottom();
      });
      
      // メッセージが削除された時の処理
      // エンドポイント「message_deleted」で指定したデータを受け取り、コールバック関数の引数(data)に格納
      socket.on('message_deleted', function(data) {
        // HTMLのdata-message-idの要素を取得して削除依頼されたメッセージidをmessageElementに格納&削除
          const messageElement = document.querySelector(`[data-message-id="${data.message_id}"]`);
          if (messageElement) {
              messageElement.remove();
          }
      });
      
      // メッセージをチャットに追加する関数（オブジェクト）
      function addMessageToChat(data) {
        //メッセージ一覧の箱を取得する
          const messagesContainer = document.getElementById('messages-container');// HTMLのmessages-containerを取得して変数に格納
          if (!messagesContainer) return;// メッセージコンテナが存在しない場合は処理終了
          
          // 日付ごとのグループを探す
          let dateGroup = document.querySelector(`[data-date="${data.date_only}"]`);
          // もし日付グループが存在しない場合、処理を続行（グループ化するための要素（dateGrop）を作成）
          if (!dateGroup) {
              // 新しい日付の場合、日付ヘッダーとグループのdivを作成
              // 日付ヘッダーを作成
              const dateHeader = document.createElement('div');
              dateHeader.className = 'date-divider text-center my-3';
              dateHeader.setAttribute('data-date-header', data.date_only);
              dateHeader.innerHTML = `<span class="date-label bg-light px-3 py-1 rounded">${data.date_only}</span>`;
              messagesContainer.appendChild(dateHeader); // 作成した日付ヘッダーをメッセージコンテナに追加
              // 日付グループを作成
              dateGroup = document.createElement('div');
              dateGroup.setAttribute('data-date', data.date_only);
              dateGroup.className = 'date-group';
              messagesContainer.appendChild(dateGroup);
          }
          
          // メッセージが自分のものかどうかを判定
          // 自分のメッセージかどうかを判定、同じならtrue、違うならfalse
          const isMyMessage = data.user_id === currentUserId;
          //判定した結果を元にtrueならmy-message、falseならother-messageを格納
          const messageClass = isMyMessage ? 'my-message' : 'other-message';
          
          // メッセージを表示する要素の作成
          const messageElement = document.createElement('div');// メッセージ要素を作成
          messageElement.className = `message ${messageClass}`;//先ほどの判定結果を元にクラスを格納
          messageElement.setAttribute('data-message-id', data.message_id || '');// メッセージIDをdata-message-id属性に設定
          
          // .split()メソッドを使って取得したformatted_timeを配列に変えて時間だけを取得
          const timeOnly = data.formatted_time.split(' ')[1] || data.formatted_time;
          
          let messageHTML = `
              <p class="message-user">${data.user_name}</p>
              <p class="message-text">${data.message}</p>
              <p class="message-time">${timeOnly}</p>
          `;
          
          // 自分のメッセージの場合は削除ボタンを追加
          if (isMyMessage && data.message_id) {
              messageHTML += `
                  <form method="POST" action="/channels/${currentChannelId}/messages/${data.message_id}">
                      <button type="submit" class="message-delete-button">
                          <ion-icon name="trash-bin-outline"></ion-icon>
                      </button>
                  </form>
              `;
          }
          
          messageElement.innerHTML = messageHTML;
          dateGroup.appendChild(messageElement);
      }
      
      // チャットの最下部にスクロール
      function scrollToBottom() {
          const messagesContainer = document.getElementById('messages-container');
          if (messagesContainer) {
              messagesContainer.scrollTop = messagesContainer.scrollHeight;
          }
      }
      
      // メッセージフォームの送信処理
      const messageForm = document.getElementById('message-form');
      if (messageForm) {
          messageForm.addEventListener('submit', function(e) {
              // フォーム送信後、入力フィールドをクリアしてフォーカスを戻す
              setTimeout(function() {
                  const messageInput = document.getElementById('message-input');
                  if (messageInput) {
                      messageInput.value = '';
                      messageInput.focus(); // フォーカスを戻す
                  }
              }, 100);
          });
      }
      
      // Enterキーでメッセージ送信（Shift+Enterで改行）
      const messageInput = document.getElementById('message-input');
      if (messageInput) {
          messageInput.addEventListener('keydown', function(e) {
              if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  messageForm.submit();
              }
          });
      }
      
      // ページ遷移時にチャンネルから離脱
      // beforeunloadはページが閉じられる、リロードする、ページ遷移する前に実行するJSの決まり関数
      window.addEventListener('beforeunload', function() {
          if (currentChannelId) {
              socket.emit('leave_channel', {channel_id: currentChannelId});
          }
      });
      
      // 初期読み込み時に最下部にスクロール
      scrollToBottom();
  });

