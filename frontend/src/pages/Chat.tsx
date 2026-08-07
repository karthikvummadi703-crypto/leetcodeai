import React, { memo, useCallback, useRef, useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import javascript from "react-syntax-highlighter/dist/esm/languages/prism/javascript";
import typescript from "react-syntax-highlighter/dist/esm/languages/prism/typescript";
import java from "react-syntax-highlighter/dist/esm/languages/prism/java";
import cpp from "react-syntax-highlighter/dist/esm/languages/prism/cpp";
import c from "react-syntax-highlighter/dist/esm/languages/prism/c";
import csharp from "react-syntax-highlighter/dist/esm/languages/prism/csharp";
import go from "react-syntax-highlighter/dist/esm/languages/prism/go";
import rust from "react-syntax-highlighter/dist/esm/languages/prism/rust";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import sql from "react-syntax-highlighter/dist/esm/languages/prism/sql";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";

// Register only the languages we commonly surface so the syntax
// highlighter stays lightweight.
SyntaxHighlighter.registerLanguage("python", python);
SyntaxHighlighter.registerLanguage("javascript", javascript);
SyntaxHighlighter.registerLanguage("typescript", typescript);
SyntaxHighlighter.registerLanguage("java", java);
SyntaxHighlighter.registerLanguage("cpp", cpp);
SyntaxHighlighter.registerLanguage("c", c);
SyntaxHighlighter.registerLanguage("csharp", csharp);
SyntaxHighlighter.registerLanguage("go", go);
SyntaxHighlighter.registerLanguage("rust", rust);
SyntaxHighlighter.registerLanguage("bash", bash);
SyntaxHighlighter.registerLanguage("sql", sql);
SyntaxHighlighter.registerLanguage("json", json);
import {
  Send,
  Copy,
  Check,
  RefreshCcw,
  Square,
  Bot,
  User as UserIcon,
  Lightbulb,
  GitPullRequest,
  ListTree,
  Network,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { useChatHistory } from "@/contexts/ChatHistoryContext";
import { useToast } from "@/components/Toast";
import {
  createConversation,
  loadConversation,
  streamChat,
  truncateLastTurn,
  type ChatMessage,
} from "@/lib/api";

interface Message extends ChatMessage {}

const SUGGESTIONS = [
  {
    icon: <Lightbulb className="h-5 w-5 text-yellow-500" />,
    title: "Explain a Problem",
    prompt: "Can you explain the Two Sum problem? I don't need the code yet, just help me understand the objective."
  },
  {
    icon: <GitPullRequest className="h-5 w-5 text-blue-500" />,
    title: "Get a Hint",
    prompt: "I'm stuck on Longest Substring Without Repeating Characters. Can you give me a hint without giving away the solution?"
  },
  {
    icon: <ListTree className="h-5 w-5 text-green-500" />,
    title: "Complexity Analysis",
    prompt: "What is the time and space complexity of merge sort? Please explain step-by-step."
  },
  {
    icon: <Network className="h-5 w-5 text-purple-500" />,
    title: "Pattern Explanation",
    prompt: "Explain the Sliding Window pattern. What kind of problems is it good for?"
  }
];

// A single chat bubble. Memoized so streaming updates to one message do not
// re-render the rest of the conversation.
const MessageBubble = memo(function MessageBubble({
  msg,
  copiedId,
  onCopy,
}: {
  msg: Message;
  copiedId: string | null;
  onCopy: (text: string, id: string) => void;
}) {
  if (msg.isStreaming && !msg.content) return null;

  return (
    <div
      className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
    >
      {msg.role === "assistant" && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30 mt-1">
          <Bot className="h-5 w-5 text-primary" />
        </div>
      )}

      <div
        className={`max-w-[85%] rounded-2xl p-4 ${
          msg.role === "user"
            ? "bg-primary text-primary-foreground rounded-tr-sm"
            : "glass-card border border-border/50 rounded-tl-sm"
        }`}
      >
        {msg.role === "user" ? (
          <div className="whitespace-pre-wrap">{msg.content}</div>
        ) : (
          <div className="prose prose-invert max-w-none text-foreground prose-p:leading-relaxed prose-pre:p-0 prose-pre:bg-transparent">
            <ReactMarkdown
              components={{
                code({
                  className,
                  children,
                  ...props
                }: React.ComponentPropsWithoutRef<"code">) {
                  const match = /language-(\w+)/.exec(className || "");
                  const code = String(children).replace(/\n$/, "");
                  if (match) {
                    const copyKey = msg.id + match[1];
                    return (
                      <div className="relative mt-4 mb-4 rounded-md overflow-hidden border border-border/50">
                        <div className="flex items-center justify-between px-4 py-1.5 bg-[#1e1e1e] border-b border-[#2d2d2d]">
                          <span className="text-xs text-gray-400 font-mono">{match[1]}</span>
                          <button
                            type="button"
                            onClick={() => onCopy(code, copyKey)}
                            aria-label="Copy code"
                            className="text-gray-400 hover:text-gray-200 transition-colors"
                          >
                            {copiedId === copyKey ? (
                              <Check className="h-4 w-4 text-green-500" />
                            ) : (
                              <Copy className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                        <SyntaxHighlighter
                          {...props}
                          style={vscDarkPlus}
                          language={match[1]}
                          PreTag="div"
                          customStyle={{ margin: 0, borderRadius: 0, padding: "1rem" }}
                        >
                          {code}
                        </SyntaxHighlighter>
                      </div>
                    );
                  }
                  return (
                    <code {...props} className="bg-muted px-1.5 py-0.5 rounded-md text-primary font-mono text-sm">
                      {children}
                    </code>
                  );
                }
              }}
            >
              {msg.content}
            </ReactMarkdown>
            {msg.isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-primary/70 animate-pulse align-middle" />
            )}
          </div>
        )}
      </div>

      {msg.role === "user" && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary/20 flex items-center justify-center border border-secondary/30 mt-1">
          <UserIcon className="h-5 w-5 text-secondary" />
        </div>
      )}
    </div>
  );
});

const Chat = () => {
  const { user } = useAuth();
  const { refresh } = useChatHistory();
  const { toast } = useToast();
  const [searchParams] = useSearchParams();
  const convParam = searchParams.get("conv");

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(true);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load an existing conversation (via ?conv=). A fresh conversation is
  // created lazily on the first message so we never persist empty ones.
  useEffect(() => {
    let cancelled = false;
    setMessages([]);
    setStreamError(null);
    setConversationId(null);

    if (convParam) {
      setLoadingConversation(true);
      loadConversation(user, convParam)
        .then((conv) => {
          if (cancelled) return;
          setConversationId(conv.id);
          setMessages(conv.messages.map((m) => ({ ...m })));
        })
        .catch(() => {
          if (!cancelled) {
            setStreamError("Could not load this conversation.");
            toast("Could not load this conversation", "error");
          }
        })
        .finally(() => {
          if (!cancelled) setLoadingConversation(false);
        });
    } else {
      setLoadingConversation(false);
    }

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [convParam]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const copyToClipboard = useCallback((text: string, id: string) => {
    void navigator.clipboard.writeText(text);
    setCopiedId(id);
    window.setTimeout(() => setCopiedId(null), 2000);
  }, []);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isTyping || loadingConversation) return;

    // Ensure a conversation exists (create lazily if the bootstrapped one failed).
    let convId = conversationId;
    if (!convId) {
      try {
        convId = await createConversation(user);
        setConversationId(convId);
      } catch {
        setStreamError("Could not connect to the assistant. Please try again in a moment.");
        toast("Could not connect to the assistant", "error");
        return;
      }
    }

    const now = new Date().toISOString();
    const userMessage: Message = {
      id: `${Date.now()}-user`,
      role: "user",
      content: trimmed,
      timestamp: now,
    };
    const assistantId = `${Date.now()}-assistant`;
    const assistantMessage: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: now,
      isStreaming: true,
    };

    setMessages(prev => [...prev, userMessage, assistantMessage]);
    setInput("");
    setIsTyping(true);
    setStreamError(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const full = await streamChat(
        user,
        convId,
        trimmed,
        (chunk) => {
          setMessages(prev =>
            prev.map(m =>
              m.id === assistantId ? { ...m, content: m.content + chunk } : m,
            ),
          );
        },
        controller.signal,
      );

      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId ? { ...m, content: full, isStreaming: false } : m,
        ),
      );
      void refresh();
    } catch (err) {
      const aborted = err instanceof DOMException && err.name === "AbortError";
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId ? { ...m, isStreaming: false } : m,
        ),
      );
      if (!aborted) {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId && !m.content
              ? { ...m, content: "I hit a problem generating a response. Please try again." }
              : m,
          ),
        );
        setStreamError("Something went wrong while generating a response. Please try again.");
        toast("Something went wrong while generating a response", "error");
      }
    } finally {
      abortRef.current = null;
      setIsTyping(false);
    }
  };

  const handleSend = () => {
    void sendMessage(input);
  };

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const handleRegenerate = async () => {
    if (isTyping || !conversationId) return;

    let cutIndex = messages.length;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        cutIndex = i;
        break;
      }
    }
    const lastUser = messages[cutIndex];
    if (!lastUser) return;

    // Drop the last user turn + its response locally, remove it from the
    // persisted store, then re-ask the same question.
    setMessages(messages.slice(0, cutIndex));
    try {
      await truncateLastTurn(user, conversationId);
    } catch (err) {
      console.error("Failed to truncate last turn", err);
    }
    void sendMessage(lastUser.content);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Show the animated dots only while the model hasn't produced any tokens yet.
  const showTypingDots =
    isTyping &&
    !messages.some(m => m.isStreaming && m.content.length > 0);

  return (
    <div className="flex flex-col h-full bg-background relative">
      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto pb-32 pt-4 px-4 md:px-8" aria-label="Chat messages">
        {loadingConversation ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="h-6 w-6 text-primary animate-spin" />
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center max-w-3xl mx-auto text-center px-4">
            <div className="mb-8">
              <h1 className="text-4xl md:text-5xl font-bold mb-4">LeetCode Guidance AI</h1>
              <p className="text-xl text-muted-foreground">Your Personal DSA Mentor</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
              {SUGGESTIONS.map((suggestion, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setInput(suggestion.prompt)}
                  className="glass-card p-4 rounded-xl text-left hover:bg-card/80 transition-colors border border-border/50 group"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-background/50 rounded-lg group-hover:scale-110 transition-transform">
                      {suggestion.icon}
                    </div>
                    <span className="font-semibold">{suggestion.title}</span>
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {suggestion.prompt}
                  </p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-6 pb-4">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                copiedId={copiedId}
                onCopy={copyToClipboard}
              />
            ))}

            {showTypingDots && (
              <div className="flex gap-4 justify-start" aria-label="Assistant is typing">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30 mt-1">
                  <Bot className="h-5 w-5 text-primary" />
                </div>
                <div className="glass-card border border-border/50 rounded-2xl rounded-tl-sm p-4 flex items-center gap-2 h-12">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "0ms" }}></div>
                    <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "150ms" }}></div>
                    <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "300ms" }}></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="absolute bottom-0 w-full bg-gradient-to-t from-background via-background to-transparent pb-6 pt-10 px-4 md:px-8">
        <div className="max-w-3xl mx-auto relative">
          {/* Generation Controls */}
          {messages.length > 0 && (
            <div className="absolute -top-12 left-0 right-0 flex justify-center gap-2">
              {isTyping ? (
                <Button variant="outline" size="sm" onClick={handleStop} className="bg-background/80 backdrop-blur-md rounded-full text-xs">
                  <Square className="h-3 w-3 mr-2" /> Stop generating
                </Button>
              ) : (
                <Button variant="outline" size="sm" onClick={handleRegenerate} className="bg-background/80 backdrop-blur-md rounded-full text-xs">
                  <RefreshCcw className="h-3 w-3 mr-2" /> Regenerate response
                </Button>
              )}
            </div>
          )}

          {streamError && (
            <div className="absolute -top-9 left-0 right-0 flex justify-center" role="alert">
              <span className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-full px-3 py-1">
                {streamError}
              </span>
            </div>
          )}

          <div className="glass-card rounded-2xl border border-border/50 shadow-2xl p-2 flex items-end gap-2 bg-card/80 backdrop-blur-xl">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message LeetCode Guidance AI..."
              aria-label="Message LeetCode Guidance AI"
              className="w-full max-h-48 min-h-[44px] bg-transparent resize-none focus:outline-none py-3 text-sm scrollbar-thin"
              rows={1}
            />

            <Button
              onClick={handleSend}
              disabled={!input.trim() || isTyping || loadingConversation}
              aria-label="Send message"
              size="icon"
              className={`flex-shrink-0 mb-1 rounded-xl transition-all ${input.trim() && !isTyping ? 'bg-primary text-primary-foreground hover:bg-primary/90' : 'bg-muted text-muted-foreground'}`}
            >
              <Send className="h-5 w-5" />
            </Button>
          </div>
          <div className="text-center mt-2">
            <span className="text-[10px] text-muted-foreground">
              LeetCode Guidance AI can make mistakes. Consider verifying important information.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
