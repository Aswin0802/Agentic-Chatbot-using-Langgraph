import streamlit as st
from langchain_core.messages import BaseMessage,HumanMessage,AIMessage,ToolMessage
import uuid
import tempfile
import os
from backend_hitl import workflow,get_all_threads,ingest_rag_document
from langgraph.types import Command

st.set_page_config(
    page_title="LangGraph AI",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)


st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    color-scheme: dark;

    --canvas: #0B0D1A;
    --side: #090B15;
    --base: #121629;
    --surface: rgba(24, 28, 52, 0.94);
    --line: rgba(255, 255, 255, 0.09);
    --line-strong: rgba(255, 255, 255, 0.18);

    --text: #F1EFEA;
    --text-2: #C9CDDD;
    --muted: #9AA0B5;
    --faint: #6F7590;

    --amber: #FBBF24;
    --coral: #FB7185;
    --pink: #F472B6;
    --violet: #8B5CF6;
    --blue: #3B82F6;
    --cyan: #22D3EE;
    --mint: #34D399;

    --r-sm: 8px;
    --r-md: 12px;
    --r-lg: 16px;
    --r-xl: 22px;

    --ease: cubic-bezier(0.2, 0.8, 0.2, 1);
    --shadow-1: 0 8px 24px rgba(0, 0, 0, 0.30);
    --shadow-2: 0 16px 44px rgba(0, 0, 0, 0.42);

    --gutter: 1.5rem;
    --spine: 34px;
}

* {
    scrollbar-width: thin;
    scrollbar-color: #3A3F5C transparent;
}

html {
    scroll-behavior: smooth;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}

html, body, .stApp,
[data-testid="stMarkdownContainer"],
[data-testid="stChatInput"] textarea,
.stButton button {
    font-family: 'IBM Plex Sans', system-ui, sans-serif;
}

::selection {
    background: rgba(244, 114, 182, 0.35);
    color: #FFFFFF;
}

:focus-visible {
    outline: 2px solid var(--cyan);
    outline-offset: 2px;
}

[data-stale="true"] {
    opacity: 0.92 !important;
    transition: none !important;
}

.stApp {
    background-color: var(--canvas);
    background-image:
        radial-gradient(circle at 12% 16%, rgba(139, 92, 246, 0.24), transparent 32%),
        radial-gradient(circle at 90% 10%, rgba(34, 211, 238, 0.14), transparent 30%),
        radial-gradient(circle at 82% 90%, rgba(244, 114, 182, 0.16), transparent 34%),
        radial-gradient(circle at 6% 92%, rgba(251, 191, 36, 0.10), transparent 30%),
        radial-gradient(circle, rgba(255, 255, 255, 0.07) 1px, transparent 1.2px);
    background-size: auto, auto, auto, auto, 26px 26px;
    color: var(--text);
    min-height: 100vh;
}

.stApp::before,
.stApp::after {
    content: "";
    position: fixed;
    border-radius: 50%;
    filter: blur(70px);
    pointer-events: none;
    will-change: transform;
}

.stApp::before {
    width: 420px;
    height: 420px;
    top: 6%;
    left: -120px;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.35), transparent 70%);
    animation: driftOne 14s ease-in-out infinite;
}

.stApp::after {
    width: 380px;
    height: 380px;
    bottom: 2%;
    right: -110px;
    background: radial-gradient(circle, rgba(244, 114, 182, 0.30), transparent 70%);
    animation: driftTwo 17s ease-in-out infinite;
}

[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.55'/></svg>");
    opacity: 0.05;
    mix-blend-mode: overlay;
    pointer-events: none;
}

@keyframes driftOne {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(90px, 70px) scale(1.15); }
}

@keyframes driftTwo {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(-80px, -70px) scale(1.2); }
}

@keyframes gradientMove {
    0% { background-position: 0% 50%; }
    100% { background-position: 300% 50%; }
}

@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

@keyframes borderFlow {
    0% { background-position: 0% 0%, 0% 50%; }
    100% { background-position: 0% 0%, 300% 50%; }
}

@keyframes railFlow {
    0% { background-position: 0% 0%; }
    100% { background-position: 0% 300%; }
}

@keyframes spineFlow {
    0% { background-position: 0 0; }
    100% { background-position: 0 480px; }
}

@keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes heroIn {
    from { opacity: 0; transform: translateY(-16px) scale(0.985); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes messageIn {
    from { opacity: 0; transform: translateY(14px) scale(0.985); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(52, 211, 153, 0); }
    100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }
}

@keyframes pulseAmber {
    0% { box-shadow: 0 0 0 0 rgba(251, 191, 36, 0.75); }
    70% { box-shadow: 0 0 0 9px rgba(251, 191, 36, 0); }
    100% { box-shadow: 0 0 0 0 rgba(251, 191, 36, 0); }
}

header[data-testid="stHeader"] {
    background: transparent;
    visibility: visible;
}

header[data-testid="stHeader"]::after {
    content: "";
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(
        90deg,
        var(--amber),
        var(--pink),
        var(--violet),
        var(--cyan),
        var(--amber)
    );
    background-size: 300% 100%;
    animation: gradientMove 8s linear infinite;
    pointer-events: none;
    transition: height 0.3s ease;
}

.stApp[data-teststate="running"] header[data-testid="stHeader"]::after {
    height: 3px;
    animation-duration: 1.4s;
}

[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] {
    visibility: hidden;
}

[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"] {
    visibility: visible !important;
    color: var(--muted);
}

[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"] button {
    color: var(--muted);
    background: transparent;
    transition: color 0.25s ease, background 0.25s ease, transform 0.25s ease;
}

[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stExpandSidebarButton"]:hover,
[data-testid="collapsedControl"] button:hover {
    color: var(--pink);
    background: rgba(244, 114, 182, 0.12);
    transform: scale(1.1);
}

.block-container {
    position: relative;
    max-width: 800px;
    padding: 3rem var(--gutter) 9rem var(--gutter);
}

.block-container > [data-testid="stVerticalBlock"] {
    position: relative;
}

.stApp:has([data-testid="stChatMessage"]) .block-container > [data-testid="stVerticalBlock"]::before {
    content: "";
    position: absolute;
    left: var(--spine);
    top: 40px;
    bottom: 0;
    width: 2px;
    border-radius: 2px;
    background: linear-gradient(
        180deg,
        var(--cyan),
        var(--violet),
        var(--pink),
        var(--amber),
        var(--cyan)
    );
    background-size: 100% 480px;
    animation: spineFlow 7s linear infinite;
    opacity: 0.7;
    pointer-events: none;
}

.hero {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 14px 24px;
    padding: 22px 26px;
    margin-bottom: 26px;
    border: 1px solid transparent;
    border-radius: var(--r-xl);
    background:
        linear-gradient(rgba(14, 17, 34, 0.96), rgba(14, 17, 34, 0.96)) padding-box,
        linear-gradient(
            120deg,
            rgba(251, 191, 36, 0.60),
            rgba(244, 114, 182, 0.55),
            rgba(139, 92, 246, 0.60),
            rgba(34, 211, 238, 0.55),
            rgba(251, 191, 36, 0.60)
        ) border-box;
    background-size: 100% 100%, 300% 100%;
    box-shadow: var(--shadow-2), 0 0 40px rgba(139, 92, 246, 0.14);
    animation:
        heroIn 0.8s var(--ease) both,
        borderFlow 12s linear infinite;
    transition: padding 0.3s ease;
}

.hero h1 {
    font-family: 'Bricolage Grotesque', sans-serif;
    font-size: 40px !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em;
    text-align: left;
    margin: 0 0 4px 0 !important;
    padding: 0;
    background: linear-gradient(
        90deg,
        var(--amber),
        var(--coral),
        var(--pink),
        var(--violet),
        var(--cyan),
        var(--amber)
    );
    background-size: 300% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradientMove 9s linear infinite;
}

.subtitle {
    text-align: left;
    color: var(--muted);
    font-size: 15px;
    margin: 0;
}

.status {
    display: flex;
    align-items: center;
    gap: 10px;
    width: fit-content;
    padding: 7px 15px 7px 13px;
    border: 1px solid rgba(52, 211, 153, 0.35);
    border-radius: 999px;
    background: rgba(52, 211, 153, 0.08);
    color: #A7F3D0;
    font-size: 13px;
    font-weight: 500;
    transition: background 0.3s ease, border-color 0.3s ease, color 0.3s ease;
}

.status-dot {
    width: 8px;
    height: 8px;
    background: var(--mint);
    border-radius: 50%;
    animation: pulse 2s ease-out infinite;
}

.s-run {
    display: none;
}

.stApp[data-teststate="running"] .status {
    border-color: rgba(251, 191, 36, 0.45);
    background: rgba(251, 191, 36, 0.10);
    color: #FDE68A;
}

.stApp[data-teststate="running"] .status-dot {
    background: var(--amber);
    animation: pulseAmber 1s ease-out infinite;
}

.stApp[data-teststate="running"] .s-on {
    display: none;
}

.stApp[data-teststate="running"] .s-run {
    display: inline;
}

.stApp:has([data-testid="stChatMessage"]) .welcome,
.stApp:has([data-testid="stChatMessage"]) .subtitle {
    display: none;
}

.stApp:has([data-testid="stChatMessage"]) .hero {
    padding: 14px 22px;
}

.stApp:has([data-testid="stChatMessage"]) .hero h1 {
    font-size: 28px !important;
    margin-bottom: 0 !important;
}

.welcome {
    padding: 34px 4px 10px 4px;
    animation: fadeUp 0.8s 0.25s var(--ease) both;
}

.welcome-title {
    font-family: 'Bricolage Grotesque', sans-serif;
    font-size: 34px;
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -0.02em;
    color: var(--text);
    margin-bottom: 8px;
}

.welcome-sub {
    color: var(--muted);
    font-size: 15.5px;
    line-height: 1.6;
    max-width: 52ch;
    margin-bottom: 26px;
}

.hints {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
}

.hint {
    position: relative;
    padding: 14px 16px 14px 18px;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--surface);
    overflow: hidden;
    animation: fadeUp 0.7s var(--ease) both;
}

.hint:nth-child(1) { animation-delay: 0.40s; --tone: var(--cyan); }
.hint:nth-child(2) { animation-delay: 0.50s; --tone: var(--coral); }
.hint:nth-child(3) { animation-delay: 0.60s; --tone: var(--amber); }
.hint:nth-child(4) { animation-delay: 0.70s; --tone: var(--violet); }

.hint::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: var(--tone);
    box-shadow: 0 0 14px var(--tone);
}

.hint-k {
    display: block;
    font-family: 'Bricolage Grotesque', sans-serif;
    font-weight: 700;
    font-size: 15px;
    color: var(--tone);
    margin-bottom: 4px;
}

.hint-t {
    display: block;
    font-size: 14px;
    line-height: 1.5;
    color: var(--text-2);
}

[data-testid="stChatMessage"] {
    position: relative;
    z-index: 1;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    padding: 14px 18px;
    margin: 0;
    gap: 14px;
    transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
}

.block-container > [data-testid="stVerticalBlock"] > div:nth-last-child(-n+2) [data-testid="stChatMessage"] {
    animation: messageIn 0.45s var(--ease) both;
}

@media (hover: hover) {
    [data-testid="stChatMessage"]:hover {
        transform: translateY(-2px);
        border-color: var(--line-strong);
        box-shadow: var(--shadow-1);
    }
}

[data-testid="stChatMessage"]:has(
    [data-testid="chatAvatarIcon-user"]
),
[data-testid="stChatMessage"]:has(
    [data-testid="stChatMessageAvatarUser"]
) {
    background:
        linear-gradient(135deg, rgba(59, 130, 246, 0.30), rgba(139, 92, 246, 0.24)),
        var(--base);
    border-color: rgba(139, 92, 246, 0.40);
}

[data-testid="stChatMessage"]:has(
    [data-testid="chatAvatarIcon-assistant"]
),
[data-testid="stChatMessage"]:has(
    [data-testid="stChatMessageAvatarAssistant"]
) {
    background:
        linear-gradient(135deg, rgba(30, 34, 60, 0.9), rgba(18, 21, 40, 0.9)),
        var(--base);
}

[data-testid="stChatMessage"]:has(
    [data-testid="chatAvatarIcon-assistant"]
)::before,
[data-testid="stChatMessage"]:has(
    [data-testid="stChatMessageAvatarAssistant"]
)::before {
    content: "";
    position: absolute;
    right: 0;
    top: 16px;
    bottom: 16px;
    width: 3px;
    border-radius: 3px 0 0 3px;
    background: linear-gradient(
        180deg,
        var(--amber),
        var(--pink),
        var(--violet),
        var(--cyan)
    );
    background-size: 100% 300%;
    animation: railFlow 6s linear infinite;
}

[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"] {
    width: 32px;
    height: 32px;
    flex-shrink: 0;
}

[data-testid="stChatMessageAvatarUser"] {
    background: linear-gradient(135deg, var(--cyan), var(--violet));
    color: #FFFFFF;
    box-shadow:
        0 0 0 3px var(--canvas),
        0 0 0 4px rgba(34, 211, 238, 0.75),
        0 0 18px rgba(34, 211, 238, 0.40);
}

[data-testid="stChatMessageAvatarAssistant"] {
    background: linear-gradient(135deg, var(--amber), var(--pink));
    color: #1A1030;
    box-shadow:
        0 0 0 3px var(--canvas),
        0 0 0 4px rgba(244, 114, 182, 0.75),
        0 0 18px rgba(244, 114, 182, 0.45);
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
    font-size: 15.5px;
    line-height: 1.68;
    max-width: 74ch;
}

[data-testid="stChatMessage"] strong {
    color: #FFFFFF;
}

[data-testid="stChatMessage"] a {
    color: var(--cyan);
    text-decoration-color: rgba(34, 211, 238, 0.4);
    text-underline-offset: 3px;
}

[data-testid="stChatMessage"] li::marker {
    color: var(--pink);
}

[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3,
[data-testid="stChatMessage"] h4 {
    font-family: 'Bricolage Grotesque', sans-serif;
    letter-spacing: -0.01em;
    color: #FFFFFF;
    margin: 1.1em 0 0.4em 0;
    padding: 0;
}

[data-testid="stChatMessage"] h1 { font-size: 24px; }
[data-testid="stChatMessage"] h2 { font-size: 20px; }
[data-testid="stChatMessage"] h3 { font-size: 17.5px; }
[data-testid="stChatMessage"] h4 { font-size: 16px; }

[data-testid="stChatMessage"] blockquote {
    margin: 0.8em 0;
    padding: 8px 16px;
    border-left: 3px solid var(--violet);
    border-radius: 0 10px 10px 0;
    background: rgba(139, 92, 246, 0.09);
    color: #D6D9E8;
}

[data-testid="stChatMessage"] table {
    border-collapse: separate;
    border-spacing: 0;
    border: 1px solid var(--line);
    border-radius: 10px;
    overflow: hidden;
}

[data-testid="stChatMessage"] th {
    background: rgba(255, 255, 255, 0.06);
    color: #FFFFFF;
}

[data-testid="stChatMessage"] th,
[data-testid="stChatMessage"] td {
    border: none;
    border-bottom: 1px solid var(--line);
    padding: 8px 12px;
}

[data-testid="stChatMessage"] hr {
    border-color: var(--line);
}

code,
pre {
    font-family: 'IBM Plex Mono', monospace !important;
}

[data-testid="stChatMessage"] pre {
    background: rgba(7, 9, 20, 0.88) !important;
    border: 1px solid var(--line);
    border-radius: var(--r-md);
}

[data-testid="stChatMessage"] :not(pre) > code {
    background: rgba(244, 114, 182, 0.14);
    color: #FBCFE8;
    border-radius: 6px;
    padding: 1px 6px;
}

[data-testid="stBottom"] {
    background: transparent;
}

[data-testid="stBottom"] > div {
    background: linear-gradient(
        to top,
        rgba(11, 13, 26, 0.96) 58%,
        rgba(11, 13, 26, 0)
    );
}

[data-testid="stBottomBlockContainer"] {
    max-width: 800px;
    padding: 28px var(--gutter) calc(1.25rem + env(safe-area-inset-bottom, 0px)) var(--gutter);
}

[data-testid="stChatInput"] {
    border: 1px solid transparent;
    border-radius: 18px;
    background:
        linear-gradient(rgba(16, 19, 38, 0.96), rgba(16, 19, 38, 0.96)) padding-box,
        linear-gradient(90deg, rgba(255,255,255,0.14), rgba(255,255,255,0.14)) border-box;
    box-shadow: var(--shadow-2);
    transition: box-shadow 0.35s ease, transform 0.35s ease;
}

[data-testid="stChatInput"]:focus-within {
    background:
        linear-gradient(rgba(16, 19, 38, 0.98), rgba(16, 19, 38, 0.98)) padding-box,
        linear-gradient(
            90deg,
            var(--amber),
            var(--pink),
            var(--violet),
            var(--cyan),
            var(--amber)
        ) border-box;
    background-size: 100% 100%, 300% 100%;
    animation: borderFlow 4s linear infinite;
    box-shadow:
        var(--shadow-2),
        0 0 30px rgba(139, 92, 246, 0.28);
    transform: translateY(-2px);
}

[data-testid="stChatInput"] textarea {
    color: var(--text) !important;
    font-size: 15px;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: var(--faint);
}

[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, var(--amber), var(--pink));
    color: #1A1030;
    border-radius: var(--r-md);
    transition: transform 0.25s ease, box-shadow 0.25s ease, opacity 0.25s ease;
}

[data-testid="stChatInput"] button:disabled {
    opacity: 0.35;
}

[data-testid="stChatInput"] button:hover:not(:disabled) {
    transform: scale(1.1) rotate(-6deg);
    box-shadow: 0 0 18px rgba(244, 114, 182, 0.55);
}

[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at 0% 0%, rgba(139, 92, 246, 0.20), transparent 45%),
        radial-gradient(circle at 100% 100%, rgba(34, 211, 238, 0.12), transparent 45%),
        var(--side);
    border-right: 1px solid var(--line);
}

[data-testid="stSidebar"] h1 {
    font-family: 'Bricolage Grotesque', sans-serif;
    font-size: 24px !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, var(--amber), var(--pink), var(--violet));
    background-size: 200% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradientMove 8s linear infinite;
}

[data-testid="stSidebar"] .stButton {
    width: 100%;
}

[data-testid="stSidebar"] .stButton button {
    width: 100%;
    justify-content: flex-start;
    text-align: left;
    background: rgba(255, 255, 255, 0.03);
    color: var(--muted);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    padding: 10px 12px;
    transition:
        transform 0.25s ease,
        background 0.25s ease,
        color 0.25s ease,
        border-color 0.25s ease,
        box-shadow 0.25s ease;
}

[data-testid="stSidebar"] .stButton button::before {
    content: "";
    flex-shrink: 0;
    width: 9px;
    height: 9px;
    margin-right: 11px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--cyan), var(--violet));
    box-shadow: 0 0 10px rgba(34, 211, 238, 0.55);
    transition: transform 0.25s ease, background 0.25s ease;
}

[data-testid="stSidebar"] .stButton button p {
    width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: left;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12.5px;
}

@media (hover: hover) {
    [data-testid="stSidebar"] .stButton button:hover {
        transform: translateX(5px);
        background: linear-gradient(
            90deg,
            rgba(139, 92, 246, 0.22),
            rgba(244, 114, 182, 0.10)
        );
        color: #FFFFFF;
        border-color: rgba(244, 114, 182, 0.45);
        box-shadow: 0 8px 22px rgba(139, 92, 246, 0.25);
    }

    [data-testid="stSidebar"] .stButton button:hover::before {
        transform: scale(1.35);
        background: linear-gradient(135deg, var(--amber), var(--pink));
    }
}

[data-testid="stSidebar"] .stButton button:active {
    transform: scale(0.98);
}

[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] > div:nth-child(2) .stButton button {
    background: linear-gradient(135deg, var(--amber), var(--pink), var(--violet));
    background-size: 200% 200%;
    color: #16102A;
    font-weight: 600;
    border: none;
    border-radius: 14px;
    justify-content: center;
    padding: 11px 12px;
    animation: gradientShift 6s ease infinite;
}

[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] > div:nth-child(2) .stButton button::before {
    content: "+";
    width: auto;
    height: auto;
    margin-right: 8px;
    border-radius: 0;
    background: none;
    box-shadow: none;
    font-size: 18px;
    font-weight: 700;
    line-height: 1;
}

[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] > div:nth-child(2) .stButton button p {
    width: auto;
    text-align: center;
    font-family: 'IBM Plex Sans', system-ui, sans-serif;
    font-size: 14.5px;
}

@media (hover: hover) {
    [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] > div:nth-child(2) .stButton button:hover {
        color: #16102A;
        transform: translateY(-2px);
        box-shadow: 0 10px 26px rgba(244, 114, 182, 0.45);
    }

    [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] > div:nth-child(2) .stButton button:hover::before {
        transform: rotate(90deg);
        background: none;
    }
}

[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] > div:nth-child(3)::before {
    content: "Recent chats";
    display: block;
    margin: 14px 0 8px 4px;
    color: var(--faint);
    font-size: 12.5px;
    font-weight: 500;
    letter-spacing: 0.02em;
}

[data-testid="stSidebarUserContent"]::after {
    content: "Powered by LangGraph";
    display: block;
    margin-top: 28px;
    padding-top: 14px;
    border-top: 1px solid var(--line);
    color: var(--faint);
    font-size: 12px;
}

::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--violet), var(--pink));
    border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, var(--cyan), var(--violet));
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

@media (max-width: 640px) {
    :root {
        --gutter: 1rem;
    }

    .hero h1 {
        font-size: 30px !important;
    }

    .hero {
        padding: 18px 18px;
    }

    .welcome-title {
        font-size: 27px;
    }

    .hints {
        grid-template-columns: 1fr;
    }
}

@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation: none !important;
        transition: none !important;
    }

    html {
        scroll-behavior: auto;
    }
}

</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="hero"><div class="hero-text"><h1>🤖 LangGraph AI</h1><div class="subtitle">Intelligent conversations powered by LangGraph</div></div><div class="status"><span class="status-dot"></span><span class="s-on">AI is online</span><span class="s-run">Thinking…</span></div></div>

<div class="welcome"><div class="welcome-title">What are we building today?</div><div class="welcome-sub">Ask a question, paste an error, or think out loud. Replies stream in as they are written.</div><div class="hints"><div class="hint"><span class="hint-k">Explain</span><span class="hint-t">How does self-attention work in a transformer?</span></div><div class="hint"><span class="hint-k">Debug</span><span class="hint-t">Why does my Python loop skip the last item?</span></div><div class="hint"><span class="hint-k">Practice</span><span class="hint-t">Give me a medium graph problem to solve</span></div><div class="hint"><span class="hint-k">Plan</span><span class="hint-t">Outline a 4-week NLP study plan</span></div></div></div>
""", unsafe_allow_html=True)

# -----------------------------------------
# Thread helper functions
# -----------------------------------------


# =========================================================
# HELPERS
# =========================================================

def generate_thread_id():
    return str(uuid.uuid4())


def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].insert(0, thread_id)


def reset_chat():
    thread_id = generate_thread_id()

    st.session_state["thread_id"] = thread_id
    st.session_state["message_history"] = []
    st.session_state["pending_hitl"] = None

    add_thread(thread_id)


def get_config(thread_id=None):
    thread_id = thread_id or st.session_state["thread_id"]

    return {
        "configurable": {"thread_id": thread_id},
        "metadata": {"thread_id": thread_id},
        "run_name": "chat_trace",
    }


def load_conversation(thread_id):
    state = workflow.get_state(
        config=get_config(thread_id)
    )

    if not state or not state.values:
        return []

    return state.values.get("messages", [])


def format_messages(messages):
    history = []

    for message in messages:
        if isinstance(message, HumanMessage):
            history.append({
                "role": "user",
                "content": (
                    message.content
                    if isinstance(message.content, str)
                    else str(message.content)
                ),
            })

        elif isinstance(message, AIMessage):
            # Do not show empty assistant tool-call messages.
            if not message.content:
                continue

            history.append({
                "role": "assistant",
                "content": (
                    message.content
                    if isinstance(message.content, str)
                    else str(message.content)
                ),
                "tools": [],
            })

    return history


def extract_interrupt_payload(result):
    """Find an interrupt in a graph result or graph checkpoint."""

    if isinstance(result, dict):
        interrupts = result.get("__interrupt__", ())
        if interrupts:
            return interrupts[0].value

    try:
        snapshot = workflow.get_state(
            config=get_config()
        )

        for task in snapshot.tasks:
            for item in getattr(task, "interrupts", ()):
                return item.value

    except Exception:
        pass

    return None


def show_interrupt_payload(payload):
    """Render the payload returned by interrupt() in the frontend."""

    if isinstance(payload, dict):
        if payload.get("title"):
            st.subheader(payload["title"])

        if payload.get("question"):
            st.markdown(f"**Question:** {payload['question']}")

        if payload.get("reason"):
            st.markdown(f"**Reason:** {payload['reason']}")

        if payload.get("instruction"):
            st.info(payload["instruction"])

        # Show additional information that may be in the payload.
        known_fields = {
            "title", "question", "reason", "instruction"
        }

        for key, value in payload.items():
            if key not in known_fields:
                st.write(f"**{key.replace('_', ' ').title()}:**")
                st.write(value)

    else:
        # Your purchase_stock tool currently interrupts with a string.
        st.markdown(str(payload))


# =========================================================
# SESSION INITIALIZATION
# =========================================================

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = get_all_threads()

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_ui_history" not in st.session_state:
    st.session_state["thread_ui_history"] = {}

if "pending_hitl" not in st.session_state:
    st.session_state["pending_hitl"] = None

current_thread = st.session_state["thread_id"]

st.session_state["thread_ui_history"].setdefault(
    current_thread,
    st.session_state["message_history"],
)

add_thread(current_thread)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("My Conversations")

if st.sidebar.button(
    "➕ New Chat",
    use_container_width=True,
):
    reset_chat()
    st.rerun()

st.sidebar.divider()

for thread_id in st.session_state["chat_threads"]:
    if st.sidebar.button(
        str(thread_id),
        key=f"thread_{thread_id}",
        use_container_width=True,
    ):
        st.session_state["thread_id"] = thread_id

        if thread_id in st.session_state["thread_ui_history"]:
            st.session_state["message_history"] = (
                st.session_state["thread_ui_history"][thread_id]
            )
        else:
            messages = load_conversation(thread_id)
            history = format_messages(messages)

            st.session_state["message_history"] = history
            st.session_state["thread_ui_history"][thread_id] = history

        # Pending approvals belong to a specific thread.
        st.session_state["pending_hitl"] = None
        st.rerun()


# =========================================================
# DISPLAY CHAT HISTORY
# =========================================================

for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        tools = message.get("tools", [])

        if message["role"] == "assistant" and tools:
            with st.expander(
                f"🔧 Tools used ({len(tools)})",
                expanded=False,
            ):
                for tool in tools:
                    if tool["status"] == "Completed":
                        st.markdown(
                            f"✅ **{tool['name']}** — Completed"
                        )
                    else:
                        st.markdown(
                            f"🔧 **{tool['name']}** — Called"
                        )


# =========================================================
# GRAPH STREAMING FUNCTION
# =========================================================

def run_graph_stream(graph_input, config):
    """
    Stream a graph invocation.

    Returns:
        answer_text, called_tools, interrupted
    """

    called_tools = {}
    interrupt_found = False
    interrupt_payload = None

    def stream_response():
        nonlocal interrupt_found, interrupt_payload

        for mode, chunk in workflow.stream(
            graph_input,
            config=config,
            stream_mode=["messages", "updates"],
        ):

            # ---------------------------------------------
            # Detect HITL interrupts from graph updates
            # ---------------------------------------------

            if mode == "updates" and isinstance(chunk, dict):
                if chunk.get("__interrupt__"):
                    interrupt_found = True
                    interrupt_payload = (
                        chunk["__interrupt__"][0].value
                    )
                    continue

            # ---------------------------------------------
            # MESSAGE STREAM
            # ---------------------------------------------

            if mode == "messages":
                message_chunk, metadata = chunk

                # Do not display tool results as assistant text.
                if isinstance(message_chunk, ToolMessage):
                    continue

                tool_call_chunks = (
                    getattr(
                        message_chunk,
                        "tool_call_chunks",
                        None,
                    ) or []
                )

                for call in tool_call_chunks:
                    tool_name = call.get("name")
                    tool_id = call.get("id")
                    key = tool_id or tool_name

                    if tool_name and key not in called_tools:
                        called_tools[key] = {
                            "name": tool_name,
                            "status": "Running",
                        }

                content = getattr(
                    message_chunk,
                    "content",
                    "",
                )

                if isinstance(content, str) and content:
                    yield content

                elif isinstance(content, list):
                    for block in content:
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "text"
                        ):
                            text_content = block.get("text", "")
                            if text_content:
                                yield text_content

            # ---------------------------------------------
            # NODE UPDATES AND TOOL STATUS
            # ---------------------------------------------

            elif mode == "updates":
                for node_name, node_update in chunk.items():
                    if not isinstance(node_update, dict):
                        continue

                    messages = node_update.get("messages", [])

                    if not isinstance(messages, list):
                        messages = [messages]

                    for message in messages:

                        if isinstance(message, AIMessage):
                            for call in message.tool_calls:
                                tool_name = call["name"]
                                tool_id = call.get("id") or tool_name

                                called_tools.setdefault(
                                    tool_id,
                                    {
                                        "name": tool_name,
                                        "status": "Running",
                                    },
                                )

                        elif isinstance(message, ToolMessage):
                            tool_name = getattr(
                                message,
                                "name",
                                "Unknown tool",
                            )

                            tool_id = getattr(
                                message,
                                "tool_call_id",
                                None,
                            )

                            matching_key = (
                                tool_id
                                if tool_id in called_tools
                                else None
                            )

                            if matching_key is None:
                                matching_key = next(
                                    (
                                        key
                                        for key, item in called_tools.items()
                                        if item["name"] == tool_name
                                        and item["status"] != "Completed"
                                    ),
                                    None,
                                )

                            if matching_key is not None:
                                called_tools[matching_key][
                                    "status"
                                ] = "Completed"
                            else:
                                called_tools[
                                    tool_id or f"result_{len(called_tools)}"
                                ] = {
                                    "name": tool_name,
                                    "status": "Completed",
                                }

    # Streamlit displays the generated text.
    answer_text = st.write_stream(stream_response())

    # Some LangGraph versions expose interrupts through the
    # checkpoint snapshot rather than the streamed update.
    if not interrupt_found:
        interrupt_payload = extract_interrupt_payload({})

        if interrupt_payload is not None:
            interrupt_found = True

    return answer_text, list(called_tools.values()), (
        interrupt_found, interrupt_payload
    )


# =========================================================
# HITL APPROVAL PANEL
# =========================================================

pending = st.session_state.get("pending_hitl")

if pending and pending["thread_id"] == st.session_state["thread_id"]:

    with st.container(border=True):
        st.warning("⏸️ Human approval required")

        show_interrupt_payload(pending["payload"])

        st.caption(
            "The workflow is paused until you approve or reject this action."
        )

        col1, col2 = st.columns(2)

        with col1:
            approve_clicked = st.button(
                "✅ Approve",
                key="hitl_approve",
                type="primary",
                use_container_width=True,
            )

        with col2:
            reject_clicked = st.button(
                "❌ Reject",
                key="hitl_reject",
                use_container_width=True,
            )

        if approve_clicked or reject_clicked:
            decision = "yes" if approve_clicked else "no"

            resume_config = get_config(pending["thread_id"])

            # Remove the old request before resuming.
            st.session_state["pending_hitl"] = None

            try:
                with st.chat_message("assistant"):
                    with st.status(
                        "Resuming workflow...",
                        expanded=True,
                    ) as status:

                        answer, tools_used, interrupt_info = (
                            run_graph_stream(
                                Command(resume=decision),
                                resume_config,
                            )
                        )

                        interrupted, payload = interrupt_info

                        if interrupted:
                            st.session_state["pending_hitl"] = {
                                "thread_id": pending["thread_id"],
                                "payload": payload,
                            }

                            status.update(
                                label="Another approval is required",
                                state="complete",
                                expanded=False,
                            )

                        else:
                            status.update(
                                label="Workflow completed",
                                state="complete",
                                expanded=False,
                            )

                            if answer:
                                st.session_state[
                                    "message_history"
                                ].append({
                                    "role": "assistant",
                                    "content": answer,
                                    "tools": tools_used,
                                })

                st.session_state["thread_ui_history"][
                    pending["thread_id"]
                ] = st.session_state["message_history"]

            except Exception as error:
                st.error(f"Failed to resume workflow: {error}")

                # Keep the request visible so it can be retried.
                st.session_state["pending_hitl"] = pending

            st.rerun()


# =========================================================
# CHAT INPUT AND PDF UPLOAD
# =========================================================

# Do not accept new prompts while an approval is pending.
has_pending_approval = (
    st.session_state.get("pending_hitl") is not None
)

if has_pending_approval:
    st.chat_input(
        "Resolve the pending approval above first",
        disabled=True,
    )
else:
    submission = st.chat_input(
        "Type here",
        accept_file=True,
        file_type=["pdf"],
    )

    if submission:
        user_input = (submission.text or "").strip()
        uploaded_files = submission.files or []

        # ---------------------------------------------
        # PDF INGESTION
        # ---------------------------------------------

        if uploaded_files:
            uploaded_pdf = uploaded_files[0]
            temporary_file_path = None

            try:
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=".pdf",
                ) as temporary_file:
                    temporary_file.write(uploaded_pdf.getvalue())
                    temporary_file_path = temporary_file.name

                with st.status(
                    f"📄 Processing {uploaded_pdf.name}...",
                    expanded=True,
                ) as upload_status:

                    upload_status.write("📥 Reading PDF...")
                    upload_status.write("🧩 Processing document...")
                    upload_status.write("🧠 Creating embeddings...")
                    upload_status.write(
                        "📦 Storing document in vector database..."
                    )

                    ingest_rag_document(temporary_file_path)

                    upload_status.update(
                        label=f"✅ {uploaded_pdf.name} uploaded successfully",
                        state="complete",
                        expanded=False,
                    )

            except Exception as error:
                st.error(f"PDF processing failed: {error}")

            finally:
                if (
                    temporary_file_path
                    and os.path.exists(temporary_file_path)
                ):
                    os.remove(temporary_file_path)

        # ---------------------------------------------
        # USER MESSAGE AND GRAPH INVOCATION
        # ---------------------------------------------

        if user_input:
            st.session_state["message_history"].append({
                "role": "user",
                "content": user_input,
            })

            with st.chat_message("user"):
                st.markdown(user_input)

            config = get_config()

            try:
                with st.chat_message("assistant"):
                    with st.status(
                        "Thinking...",
                        expanded=True,
                    ) as status:

                        answer, tools_used, interrupt_info = (
                            run_graph_stream(
                                {
                                    "messages": [
                                        HumanMessage(content=user_input)
                                    ]
                                },
                                config,
                            )
                        )

                        interrupted, payload = interrupt_info

                        if interrupted:
                            # Save the pending approval for this thread.
                            st.session_state["pending_hitl"] = {
                                "thread_id": st.session_state["thread_id"],
                                "payload": payload,
                            }

                            status.update(
                                label="Waiting for human approval",
                                state="complete",
                                expanded=False,
                            )

                        else:
                            status.update(
                                label="Response complete",
                                state="complete",
                                expanded=False,
                            )

                            tools_used = tools_used or []

                            if answer:
                                st.session_state[
                                    "message_history"
                                ].append({
                                    "role": "assistant",
                                    "content": answer,
                                    "tools": tools_used,
                                })

                            if tools_used:
                                with st.expander(
                                    f"🔧 Tools used ({len(tools_used)})",
                                    expanded=False,
                                ):
                                    for tool in tools_used:
                                        if tool["status"] == "Completed":
                                            st.markdown(
                                                f"✅ **{tool['name']}** — Completed"
                                            )
                                        else:
                                            st.markdown(
                                                f"🔧 **{tool['name']}** — Called"
                                            )

            except Exception as error:
                st.error(f"Workflow execution failed: {error}")

            # Save conversation history for the selected thread.
            current_thread = st.session_state["thread_id"]

            st.session_state["thread_ui_history"][
                current_thread
            ] = st.session_state["message_history"]

            add_thread(current_thread)
            st.rerun()
