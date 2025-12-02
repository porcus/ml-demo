import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Provider = "openai" | "lmstudio";

type ProviderSelectorProps = {
  provider: Provider;
  lmstudioModel?: string;
  onProviderChange: (provider: Provider) => void;
  onLmStudioModelChange: (value: string) => void;
};

function ProviderSelector({
  provider,
  lmstudioModel,
  onProviderChange,
  onLmStudioModelChange,
}: ProviderSelectorProps) {
  return (
    <div style={styles.topBar}>
      <div>
        <label style={styles.label}>
          Provider:&nbsp;
          <select
            value={provider}
            onChange={e => onProviderChange(e.target.value as Provider)}
          >
            <option value="openai">OpenAI</option>
            <option value="lmstudio">LM Studio</option>
          </select>
        </label>
      </div>
      {provider === "lmstudio" && (
        <div>
          <label style={styles.label}>
            LM Studio model:&nbsp;
            <input
              type="text"
              placeholder="e.g. lmstudio-community/qwen2.5-7b-instruct (default: quen/quen3-v1-8b)"
              value={lmstudioModel ?? ""}
              onChange={e => onLmStudioModelChange(e.target.value)}
              style={{ width: 450 }}
            />
          </label>
        </div>
      )}
    </div>
  );
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  provider: Provider;
  timestamp: number;
}

interface Chat {
  id: string;
  title: string;
  provider: Provider;
  lmstudioModel?: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

const STORAGE_KEY = "summarizer-chats-v1";
const API_BASE_URL = "http://localhost:8000";

// ----------- localStorage helpers ------------

function loadInitialState(): { chats: Chat[]; selectedChatId: string | null } {
  if (typeof window === "undefined") {
    return { chats: [], selectedChatId: null };
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      const firstChat = createNewChat();
      return { chats: [firstChat], selectedChatId: firstChat.id };
    }
    const parsed = JSON.parse(raw) as {
      chats?: Chat[];
      selectedChatId?: string | null;
    };
    if (!parsed.chats || parsed.chats.length === 0) {
      const firstChat = createNewChat();
      return { chats: [firstChat], selectedChatId: firstChat.id };
    }
    const selected =
      parsed.selectedChatId && parsed.chats.some(c => c.id === parsed.selectedChatId)
        ? parsed.selectedChatId
        : parsed.chats[0].id;
    return { chats: parsed.chats, selectedChatId: selected };
  } catch {
    const firstChat = createNewChat();
    return { chats: [firstChat], selectedChatId: firstChat.id };
  }
}

function createNewChat(): Chat {
  const now = Date.now();
  const id = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `chat-${now}`;

  return {
    id,
    title: "New chat",
    provider: "openai",
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

// ----------- React component ------------

const initialState = loadInitialState();

function App() {
  const [chats, setChats] = useState<Chat[]>(initialState.chats);
  const [selectedChatId, setSelectedChatId] = useState<string | null>(
    initialState.selectedChatId
  );
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Persist chats + selection whenever they change
  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ chats, selectedChatId })
    );
  }, [chats, selectedChatId]);

  // Ensure there's always a selected chat if any exist
  useEffect(() => {
    if (!selectedChatId && chats.length > 0) {
      setSelectedChatId(chats[0].id);
    }
  }, [chats, selectedChatId]);

  const selectedChat = chats.find(c => c.id === selectedChatId) ?? null;

  function updateChat(chatId: string, updater: (chat: Chat) => Chat) {
    setChats(prev =>
      prev.map(chat => (chat.id === chatId ? updater(chat) : chat))
    );
  }

  function handleNewChat() {
    const newChat = createNewChat();
    setChats(prev => [newChat, ...prev]);
    setSelectedChatId(newChat.id);
    setInputText("");
    setError(null);
  }

  function handleDeleteChat(chatId: string) {
    setChats(prev => prev.filter(c => c.id !== chatId));
    if (chatId === selectedChatId) {
      const remaining = chats.filter(c => c.id !== chatId);
      setSelectedChatId(remaining.length > 0 ? remaining[0].id : null);
      setInputText("");
      setError(null);
    }
  }

  function handleProviderChange(provider: Provider) {
    if (!selectedChat) return;
    updateChat(selectedChat.id, chat => ({
      ...chat,
      provider,
      // optional: clear lmstudio model when switching away
      lmstudioModel: provider === "lmstudio" ? chat.lmstudioModel : undefined,
      updatedAt: Date.now(),
    }));
  }

  function handleLmStudioModelChange(value: string) {
    if (!selectedChat) return;
    updateChat(selectedChat.id, chat => ({
      ...chat,
      lmstudioModel: value || undefined,
      updatedAt: Date.now(),
    }));
  }

  async function handleSend(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!selectedChat) return;
    const trimmed = inputText.trim();
    if (!trimmed || isLoading) return;

    setError(null);
    setIsLoading(true);
    setInputText("");

    const now = Date.now();
    const msgId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `msg-${now}`;

    const userMessage: ChatMessage = {
      id: msgId,
      role: "user",
      content: trimmed,
      provider: selectedChat.provider,
      timestamp: now,
    };

    // Optimistically add user message
    updateChat(selectedChat.id, chat => {
      const newMessages = [...chat.messages, userMessage];
      const newTitle =
        chat.messages.length === 0
          ? trimmed.slice(0, 40) || "New chat"
          : chat.title;
      return {
        ...chat,
        title: newTitle,
        messages: newMessages,
        updatedAt: now,
      };
    });

    try {
      // Build URL with provider + optional lmstudio_model
      let url = `${API_BASE_URL}/summarize?provider=${selectedChat.provider}`;
      if (
        selectedChat.provider === "lmstudio" &&
        selectedChat.lmstudioModel
      ) {
        url += `&lmstudio_model=${encodeURIComponent(
          selectedChat.lmstudioModel
        )}`;
      }

      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmed }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(
          `API error (${response.status}): ${text || response.statusText}`
        );
      }

      const data: { summary: string } = await response.json();

      const assistantMessage: ChatMessage = {
        id:
          typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID()
            : `msg-${Date.now()}`,
        role: "assistant",
        content: data.summary,
        provider: selectedChat.provider,
        timestamp: Date.now(),
      };

      updateChat(selectedChat.id, chat => ({
        ...chat,
        messages: [...chat.messages, assistantMessage],
        updatedAt: Date.now(),
      }));
    } catch (err: any) {
      console.error(err);
      setError(err?.message ?? "Failed to call summarize API.");

      // Optionally store an "error" assistant message
      updateChat(selectedChat.id, chat => ({
        ...chat,
        messages: [
          ...chat.messages,
          {
            id:
              typeof crypto !== "undefined" && "randomUUID" in crypto
                ? crypto.randomUUID()
                : `msg-${Date.now()}`,
            role: "assistant",
            content: `Error: ${err?.message ?? "Unknown error"}`,
            provider: selectedChat.provider,
            timestamp: Date.now(),
          },
        ],
        updatedAt: Date.now(),
      }));
    } finally {
      setIsLoading(false);
    }
  }

  // ---- Render ----

  return (
    <div style={styles.app}>
      {/* Sidebar */}
      <div style={styles.sidebar}>
        <div style={styles.sidebarHeader}>
          <h2 style={{ margin: 0 }}>Summarizer Chats</h2>
          <button onClick={handleNewChat} style={styles.buttonPrimary}>
            + New chat
          </button>
        </div>
        <div style={styles.chatList}>
          {chats.map(chat => (
            <div
              key={chat.id}
              style={{
                ...styles.chatListItem,
                ...(chat.id === selectedChatId
                  ? styles.chatListItemActive
                  : {}),
              }}
              onClick={() => setSelectedChatId(chat.id)}
            >
              <div style={{ fontWeight: 600 }}>
                {chat.title || "Untitled chat"}
              </div>
              <div style={{ fontSize: 12, opacity: 0.7 }}>
                Provider: {chat.provider === "openai" ? "OpenAI" : "LM Studio"}
              </div>
              <button
                onClick={e => {
                  e.stopPropagation();
                  handleDeleteChat(chat.id);
                }}
                style={styles.deleteButton}
              >
                ✕
              </button>
            </div>
          ))}
          {chats.length === 0 && (
            <div style={{ fontSize: 14, opacity: 0.7 }}>
              No chats yet. Create one to get started.
            </div>
          )}
        </div>
      </div>

      {/* Main panel */}
      <div style={styles.main}>
        {!selectedChat ? (
          <div style={styles.emptyState}>
            <p>No chat selected.</p>
            <button onClick={handleNewChat} style={styles.buttonPrimary}>
              Start a new chat
            </button>
          </div>
        ) : (
          <>
          {/* Top bar: provider + LM Studio model */}
          {selectedChat && (
            <ProviderSelector
              provider={selectedChat.provider}
              lmstudioModel={selectedChat.lmstudioModel}
              onProviderChange={handleProviderChange}
              onLmStudioModelChange={handleLmStudioModelChange}
            />
          )}


            {/* Messages */}
            <div style={styles.messages}>
              {selectedChat.messages.length === 0 && (
                <div style={{ fontSize: 14, opacity: 0.7 }}>
                  No messages yet. Type some text below to summarize.
                </div>
              )}
              {selectedChat.messages.map(msg => (
                <div
                  key={msg.id}
                  style={{
                    ...styles.message,
                    ...(msg.role === "user"
                      ? styles.messageUser
                      : styles.messageAssistant),
                  }}
                >
                  <div style={styles.messageMeta}>
                    <span style={{ fontWeight: 600 }}>
                      {msg.role === "user" ? "You" : "Assistant"}
                    </span>
                    <span style={{ fontSize: 11, opacity: 0.7 }}>
                      {" "}
                      · {msg.provider}
                    </span>
                  </div>
                  {/* <div style={styles.messageContent}>{msg.content}</div> */}

                  <div style={styles.messageContent}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      // You can style different markdown elements via components if you like
                      components={{
                        p: ({ node, ...props }) => <p style={{ margin: "4px 0" }} {...props} />,
                        li: ({ node, ...props }) => <li style={{ marginBottom: 2 }} {...props} />,
                        code: ({ node, inline, ...props }) =>
                          inline ? (
                            <code
                              style={{
                                backgroundColor: "#f3f4f6",
                                padding: "2px 4px",
                                borderRadius: 4,
                                fontFamily: "monospace",
                              }}
                              {...props}
                            />
                          ) : (
                            <pre
                              style={{
                                backgroundColor: "#f3f4f6",
                                padding: 8,
                                borderRadius: 6,
                                overflowX: "auto",
                                fontFamily: "monospace",
                              }}
                            >
                              <code {...props} />
                            </pre>
                          ),
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>

                </div>
              ))}
            </div>

            {/* Error */}
            {error && (
              <div style={styles.errorBox}>
                <strong>Error:</strong> {error}
              </div>
            )}

            {/* Input form */}
            <form onSubmit={handleSend} style={styles.inputContainer}>
              <textarea
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                placeholder="Paste or type text to summarize..."
                style={styles.textarea}
                rows={3}
              />
              <div style={styles.inputActions}>
                <button
                  type="submit"
                  style={styles.buttonPrimary}
                  disabled={isLoading || !inputText.trim()}
                >
                  {isLoading ? "Summarizing..." : "Send"}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

// ----------- inline styles for quick layout ------------

const styles: { [key: string]: React.CSSProperties } = {
  app: {
    display: "flex",
    height: "100vh",
    fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: 14,
  },
  sidebar: {
    width: 260,
    borderRight: "1px solid #ddd",
    display: "flex",
    flexDirection: "column",
    padding: 12,
    gap: 8,
  },
  sidebarHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  chatList: {
    flex: 1,
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  chatListItem: {
    position: "relative",
    padding: "6px 28px 6px 8px",
    borderRadius: 6,
    cursor: "pointer",
    border: "1px solid transparent",
  },
  chatListItemActive: {
    backgroundColor: "#eef5ff",
    borderColor: "#b4c8ff",
  },
  deleteButton: {
    position: "absolute",
    right: 4,
    top: 4,
    border: "none",
    background: "transparent",
    cursor: "pointer",
    fontSize: 11,
    opacity: 0.6,
  },
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    padding: 16,
    gap: 8,
  },
  topBar: {
    display: "flex",
    gap: 16,
    alignItems: "center",
    marginBottom: 4,
  },
  label: {
    fontSize: 13,
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    border: "1px solid #ddd",
    borderRadius: 8,
    padding: 8,
    display: "flex",
    flexDirection: "column",
    gap: 6,
    backgroundColor: "#fafafa",
  },
  message: {
    padding: 8,
    borderRadius: 8,
    maxWidth: "80%",
    whiteSpace: "pre-wrap",
  },
  messageUser: {
    alignSelf: "flex-end",
    backgroundColor: "#dbeafe",
  },
  messageAssistant: {
    alignSelf: "flex-start",
    backgroundColor: "#e5e7eb",
  },
  messageMeta: {
    marginBottom: 4,
    fontSize: 11,
  },
  messageContent: {},
  inputContainer: {
    borderTop: "1px solid #ddd",
    paddingTop: 8,
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  textarea: {
    width: "100%",
    resize: "vertical",
    padding: 8,
    borderRadius: 6,
    border: "1px solid #ccc",
    fontFamily: "inherit",
    fontSize: "inherit",
  },
  inputActions: {
    display: "flex",
    justifyContent: "flex-end",
  },
  buttonPrimary: {
    padding: "6px 12px",
    borderRadius: 6,
    border: "none",
    backgroundColor: "#2563eb",
    color: "white",
    cursor: "pointer",
    fontSize: 13,
  },
  emptyState: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  errorBox: {
    border: "1px solid #fecaca",
    backgroundColor: "#fee2e2",
    color: "#7f1d1d",
    borderRadius: 6,
    padding: 8,
    fontSize: 13,
  },
};

export default App;
