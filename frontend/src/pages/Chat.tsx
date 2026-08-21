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

const AiOrb = ({ isTyping = false }: { isTyping?: boolean }) => (
  <div className="relative w-20 h-20 flex items-center justify-center">
    <div className={`absolute inset-0 bg-blue-500/20 rounded-full blur-[20px] ${isTyping ? 'animate-pulse' : 'animate-orb'}`} />
    <div className={`absolute inset-2 bg-blue-400/40 rounded-full blur-[10px] ${isTyping ? 'animate-bounce' : ''}`} />
    <div className="relative z-10 w-10 h-10 bg-gradient-to-br from-[#4D82FF] to-[#9EBCFF] rounded-full shadow-[0_0_20px_rgba(77,130,255,0.8)] border border-white/20 flex items-center justify-center overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(255,255,255,0.2)_100%)]" />
      <Bot className="h-5 w-5 text-white drop-shadow-md" />
    </div>
    {isTyping && (
      <div className="absolute -inset-2 border border-blue-500/30 rounded-full animate-[spin_4s_linear_infinite]" />
    )}
  </div>
);

const HexLogo = ({ size = 44 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="chatHexGrad" x1="0" y1="0" x2="64" y2="64">
        <stop offset="0%" stopColor="#4D82FF"/>
        <stop offset="100%" stopColor="#9EBCFF"/>
      </linearGradient>
    </defs>
    <path d="M32 2 L58 17 L58 47 L32 62 L6 47 L6 17 Z" fill="url(#chatHexGrad)" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
    <text x="32" y="42" textAnchor="middle" fontFamily="monospace" fontWeight="bold" fontSize="24" fill="white">&lt;/&gt;</text>
  </svg>
);

const CHIPS = [
  { label: "Explain Step-by-Step", prompt: "Can you explain this problem step-by-step?" },
  { label: "Subtle Hint", prompt: "Give me a subtle hint to point me in the right direction." },
  { label: "Optimal Complexity", prompt: "Explain the optimal solution and its complexity." },
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
      transition={{ duration: 0.5, cubicBezier: [0.16, 1, 0.3, 1] }}
      className={`flex gap-5 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
    >
      {msg.role === "assistant" && (
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 mt-1 shadow-sm">
          <Bot className="h-5 w-5 text-blue-400" />
        </div>
      )}

      <div
        className={`max-w-[85%] rounded-[1.5rem] px-5 py-4 shadow-2xl transition-all ${
          msg.role === "user"
            ? "bg-blue-600 text-white rounded-tr-sm border border-blue-400/20"
            : "glass-card border border-white/5 rounded-tl-sm text-white/90"
        }`}
      >
        {msg.role === "user" ? (
          <div className="whitespace-pre-wrap text-sm leading-relaxed font-medium">{msg.content}</div>
        ) : (
          <div className="prose prose-invert max-w-none prose-p:leading-relaxed prose-pre:p-0 prose-pre:bg-transparent">
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
                      <div className="relative mt-5 mb-5 rounded-2xl overflow-hidden border border-white/5 bg-[#0D121E]/80 backdrop-blur-md shadow-2xl">
                        <div className="flex items-center justify-between px-5 py-2.5 bg-white/[0.03] border-b border-white/5">
                          <span className="text-[10px] text-white/40 font-bold tracking-[0.2em] uppercase">{match[1]}</span>
                          <button
                            type="button"
                            onClick={() => onCopy(code, copyKey)}
                            className="text-white/30 hover:text-white transition-all flex items-center gap-2"
                          >
                            {copiedId === copyKey ? (
                              <>
                                <Check className="h-3.5 w-3.5 text-green-400" />
                                <span className="text-[10px] text-green-400 font-bold uppercase tracking-wider">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="h-3.5 w-3.5" />
                                <span className="text-[10px] font-bold uppercase tracking-wider">Copy</span>
                              </>
                            )}
                          </button>
                        </div>
                        <SyntaxHighlighter
                          {...props}
                          style={vscDarkPlus}
                          language={match[1]}
                          PreTag="div"
                          customStyle={{ margin: 0, borderRadius: 0, padding: "1.25rem", fontSize: "0.85rem", background: "transparent" }}
                        >
                          {code}
                        </SyntaxHighlighter>
                      </div>
                    );
                  }
                  return (
                    <code {...props} className="bg-white/5 px-2 py-0.5 rounded-lg text-blue-300 font-mono text-xs font-bold border border-white/5">
                      {children}
                    </code>
                  );
                }
              }}
            >
              {msg.content}
            </ReactMarkdown>
            {msg.isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-blue-500 shadow-[0_0_10px_rgba(77,130,255,0.8)] animate-pulse align-middle" />
            )}
          </div>
        )}
      </div>

      {msg.role === "user" && (
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center border border-white/10 mt-1 shadow-sm">
          <UserIcon className="h-5 w-5 text-white/40" />
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
    <div className="flex flex-col h-full bg-[#05070D] relative overflow-hidden">
      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto pb-40 pt-6 px-4 md:px-10 custom-scrollbar" aria-label="Chat messages">
        {loadingConversation ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center max-w-3xl mx-auto text-center px-6">
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.8, cubicBezier: [0.16, 1, 0.3, 1] }}
              className="mb-12 flex flex-col items-center"
            >
              <div className="mb-8">
                <AiOrb />
              </div>
              <h1 className="text-4xl md:text-5xl font-extrabold mb-4 tracking-tight text-white">LeetCode <span className="text-gradient">AI</span></h1>
              <p className="text-white/40 text-sm max-w-md font-medium leading-relaxed">
                Your elite algorithmic partner. Ask complex questions, request hints, and master coding patterns with 3D clarity.
              </p>
            </motion.div>

            {/* Quick action chips */}
            <motion.div 
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.3, cubicBezier: [0.16, 1, 0.3, 1] }}
              className="flex flex-wrap gap-3 justify-center max-w-2xl"
            >
              {CHIPS.map((chip, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setInput(chip.prompt)}
                  className="px-5 py-2.5 text-[10px] font-bold uppercase tracking-[0.15em] rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-blue-500/10 hover:border-blue-500/30 transition-all text-white/40 hover:text-white cursor-pointer shadow-lg"
                >
                  {chip.label}
                </button>
              ))}
            </motion.div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-8 pb-10">
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
              <div className="flex gap-5 justify-start" aria-label="Assistant is typing">
                <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 mt-1">
                  <Bot className="h-5 w-5 text-blue-400" />
                </div>
                <div className="glass-card border border-white/5 rounded-[1.5rem] rounded-tl-sm px-6 py-4 flex items-center gap-3 h-14 shadow-2xl bg-white/[0.03]">
                  <div className="flex space-x-1.5">
                    <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: "0ms" }}></div>
                    <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: "150ms" }}></div>
                    <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: "300ms" }}></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="absolute bottom-0 w-full bg-gradient-to-t from-[#05070D] via-[#05070D]/95 to-transparent pb-8 pt-16 px-4 md:px-10">
        <div className="max-w-3xl mx-auto relative">
          {/* Generation Controls */}
          {messages.length > 0 && (
            <div className="absolute -top-14 left-0 right-0 flex justify-center gap-3">
              {isTyping ? (
                <Button variant="outline" size="sm" onClick={handleStop} className="bg-white/5 backdrop-blur-xl rounded-full text-[10px] font-bold tracking-widest uppercase border-white/10 hover:bg-white/10 text-white/60 hover:text-white transition-all h-9 px-5">
                  <Square className="h-3 w-3 mr-2.5 fill-current" /> Stop Process
                </Button>
              ) : (
                <Button variant="outline" size="sm" onClick={handleRegenerate} className="bg-white/5 backdrop-blur-xl rounded-full text-[10px] font-bold tracking-widest uppercase border-white/10 hover:bg-white/10 text-white/60 hover:text-white transition-all h-9 px-5">
                  <RefreshCcw className="h-3 w-3 mr-2.5" /> Re-Sync Link
                </Button>
              )}
            </div>
          )}

          {streamError && (
            <div className="absolute -top-10 left-0 right-0 flex justify-center" role="alert">
              <span className="text-[10px] font-bold uppercase tracking-widest text-red-400 bg-red-500/10 border border-red-500/20 rounded-full px-4 py-1.5 backdrop-blur-md">
                {streamError}
              </span>
            </div>
          )}

          <div className="glass-card rounded-[2rem] border border-white/5 shadow-[0_30px_60px_-12px_rgba(0,0,0,0.6)] p-3 flex items-end gap-3 bg-white/[0.04] backdrop-blur-2xl">
            <button
              type="button"
              className="p-3 text-white/20 hover:text-white hover:bg-white/5 rounded-2xl transition-all"
              onClick={() => toast("Integration module pending", "info")}
            >
              <Paperclip className="h-5 w-5" />
            </button>
            
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="INITIALIZE NEURAL LINK..."
              className="w-full max-h-48 min-h-[44px] bg-transparent resize-none focus:outline-none py-3 text-sm text-white placeholder:text-white/10 font-medium tracking-tight custom-scrollbar"
              rows={1}
            />

            <Button
              onClick={handleSend}
              disabled={!input.trim() || isTyping || loadingConversation}
              size="icon"
              className={`flex-shrink-0 rounded-2xl transition-all h-11 w-11 ${
                input.trim() && !isTyping 
                  ? 'btn-gradient shadow-[0_0_20px_rgba(77,130,255,0.4)]' 
                  : 'bg-white/5 text-white/10'
              }`}
            >
              <Send className="h-5 w-5" />
            </Button>
          </div>
          <div className="text-center mt-4">
            <span className="text-[10px] font-bold uppercase tracking-[0.25em] text-white/10">
              AI Output may contain inaccuracies. Verify critical logic.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};


export default Chat;
