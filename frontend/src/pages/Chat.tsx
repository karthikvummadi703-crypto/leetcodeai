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
import { motion, AnimatePresence } from "framer-motion";

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
  Paperclip,
  Image as ImageIcon,
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

const HexLogo = ({ size = 44 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="hexLogoChat" x1="0" y1="0" x2="64" y2="64">
        <stop offset="0%" stopColor="#7c3aed"/>
        <stop offset="100%" stopColor="#3b82f6"/>
      </linearGradient>
    </defs>
    <path d="M32 2 L58 17 L58 47 L32 62 L6 47 L6 17 Z" fill="url(#hexLogoChat)" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
    <text x="32" y="42" textAnchor="middle" fontFamily="monospace" fontWeight="bold" fontSize="24" fill="white">&lt;/&gt;</text>
  </svg>
);

const CHIPS = [
  { label: "Explain", prompt: "Can you explain this problem step-by-step?" },
  { label: "Hint", prompt: "Give me a subtle hint to point me in the right direction." },
  { label: "Optimal Solution", prompt: "Explain the optimal solution for this problem." },
  { label: "Brute Force", prompt: "Explain the brute force approach first." },
  { label: "Similar Problems", prompt: "What are some similar LeetCode problems I can practice?" },
];

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
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
    >
      {msg.role === "assistant" && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30 mt-1">
          <Bot className="h-5 w-5 text-primary" />
        </div>
      )}

      <div
        className={`max-w-[85%] rounded-2xl p-4 shadow-md ${
          msg.role === "user"
            ? "bg-primary text-primary-foreground rounded-tr-sm"
            : "glass-card border border-border/50 rounded-tl-sm"
        }`}
      >
        {msg.role === "user" ? (
          <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</div>
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
                      <div className="relative mt-4 mb-4 rounded-xl overflow-hidden border border-border/50 shadow-lg">
                        <div className="flex items-center justify-between px-4 py-2 bg-[#1e1e1e] border-b border-[#2d2d2d]">
                          <span className="text-xs text-gray-400 font-mono font-semibold">{match[1]}</span>
                          <button
                            type="button"
                            onClick={() => onCopy(code, copyKey)}
                            aria-label="Copy code"
                            className="text-gray-400 hover:text-gray-200 transition-colors flex items-center gap-1.5"
                          >
                            {copiedId === copyKey ? (
                              <>
                                <Check className="h-3.5 w-3.5 text-green-500" />
                                <span className="text-[10px] text-green-500 font-semibold">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="h-3.5 w-3.5" />
                                <span className="text-[10px] font-semibold">Copy</span>
                              </>
                            )}
                          </button>
                        </div>
                        <SyntaxHighlighter
                          {...props}
                          style={vscDarkPlus}
                          language={match[1]}
                          PreTag="div"
                          customStyle={{ margin: 0, borderRadius: 0, padding: "1rem", fontSize: "0.875rem" }}
                        >
                          {code}
                        </SyntaxHighlighter>
                      </div>
                    );
                  }
                  return (
                    <code {...props} className="bg-muted px-1.5 py-0.5 rounded-md text-primary font-mono text-xs font-semibold">
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
    </motion.div>
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
  }, [convParam, user, toast]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

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

    let convId = conversationId;
    if (!convId) {
      try {
        convId = await createConversation(user, trimmed.slice(0, 30) || "New Chat");
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

  const showTypingDots =
    isTyping &&
    !messages.some(m => m.isStreaming && m.content.length > 0);

  return (
    <div className="flex flex-col h-full bg-background relative overflow-hidden">
      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto pb-32 pt-4 px-4 md:px-8" aria-label="Chat messages">
        {loadingConversation ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="h-6 w-6 text-primary animate-spin" />
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center max-w-3xl mx-auto text-center px-4">
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.4 }}
              className="mb-8 flex flex-col items-center"
            >
              <div className="mb-4">
                <HexLogo size={56} />
              </div>
              <h1 className="text-3xl md:text-4xl font-extrabold mb-2 tracking-tight">LeetCode AI</h1>
              <p className="text-muted-foreground text-sm max-w-md">
                Your AI partner for cracking technical coding interviews, master algorithms & complexity analysis.
              </p>
            </motion.div>

            {/* Quick action chips */}
            <motion.div 
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.2 }}
              className="flex flex-wrap gap-2 justify-center max-w-2xl"
            >
              {CHIPS.map((chip, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setInput(chip.prompt)}
                  className="px-4 py-2 text-xs font-semibold rounded-full border border-border/50 bg-card/60 hover:bg-primary/10 hover:border-primary/30 transition-all text-muted-foreground hover:text-foreground cursor-pointer shadow-sm"
                >
                  {chip.label}
                </button>
              ))}
            </motion.div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-6 pb-4">
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  msg={msg}
                  copiedId={copiedId}
                  onCopy={copyToClipboard}
                />
              ))}
            </AnimatePresence>

            {showTypingDots && (
              <div className="flex gap-4 justify-start animate-pulse" aria-label="Assistant is typing">
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
                <Button variant="outline" size="sm" onClick={handleStop} className="bg-background/80 backdrop-blur-md rounded-full text-xs border-border/50">
                  <Square className="h-3 w-3 mr-2" /> Stop generating
                </Button>
              ) : (
                <Button variant="outline" size="sm" onClick={handleRegenerate} className="bg-background/80 backdrop-blur-md rounded-full text-xs border-border/50">
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

          <div className="glass-card rounded-2xl border border-border/50 shadow-2xl p-2.5 flex items-end gap-2 bg-card/85 backdrop-blur-xl">
            <button
              type="button"
              className="p-2.5 text-muted-foreground hover:text-foreground hover:bg-accent/40 rounded-xl transition-colors cursor-pointer"
              onClick={() => toast("Attachments feature coming soon!", "info")}
            >
              <Paperclip className="h-4.5 w-4.5" />
            </button>
            <button
              type="button"
              className="p-2.5 text-muted-foreground hover:text-foreground hover:bg-accent/40 rounded-xl transition-colors cursor-pointer"
              onClick={() => toast("Camera/Image input coming soon!", "info")}
            >
              <ImageIcon className="h-4.5 w-4.5" />
            </button>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about DSA..."
              aria-label="Message LeetCode Guidance AI"
              className="w-full max-h-48 min-h-[40px] bg-transparent resize-none focus:outline-none py-2 text-sm scrollbar-none"
              rows={1}
            />

            <Button
              onClick={handleSend}
              disabled={!input.trim() || isTyping || loadingConversation}
              aria-label="Send message"
              size="icon"
              className={`flex-shrink-0 rounded-xl transition-all h-9 w-9 ${
                input.trim() && !isTyping 
                  ? 'btn-gradient text-white shadow-md' 
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <div className="text-center mt-2.5">
            <span className="text-[10px] text-muted-foreground/60">
              LeetCode Guidance AI can make mistakes. Consider verifying important information.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
