const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");

function randomId(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

function getSessionIds() {
  let userId = sessionStorage.getItem("user_id");
  let sessionId = sessionStorage.getItem("session_id");

  if (!userId || !sessionId) {
    userId = randomId("user");
    sessionId = randomId("session");
    sessionStorage.setItem("user_id", userId);
    sessionStorage.setItem("session_id", sessionId);
  }

  return { userId, sessionId };
}

function resetSession() {
  sessionStorage.removeItem("user_id");
  sessionStorage.removeItem("session_id");
  chatWindow.innerHTML = "";
  addMessage(
    "agent",
    "Hi! I can help with refund requests. Share your order ID (e.g. ORD-101)."
  );
}

function addMessage(role, text) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;
  bubble.textContent = text;
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return bubble;
}

async function sendMessage(message) {
  const { userId, sessionId } = getSessionIds();
  addMessage("user", message);

  const loading = addMessage("loading", "Thinking...");
  sendBtn.disabled = true;
  messageInput.disabled = true;

  try {
    const params = new URLSearchParams({
      user_id: userId,
      session_id: sessionId,
      message,
    });

    const response = await fetch(`/chat?${params.toString()}`, {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error(`Server error (${response.status})`);
    }

    const data = await response.json();
    loading.remove();
    addMessage("agent", data.reply || "No reply received.");
  } catch (error) {
    loading.remove();
    addMessage("system", `Could not reach the agent: ${error.message}`);
  } finally {
    sendBtn.disabled = false;
    messageInput.disabled = false;
    messageInput.focus();
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;
  messageInput.value = "";
  sendMessage(message);
});

newChatBtn.addEventListener("click", resetSession);

resetSession();
