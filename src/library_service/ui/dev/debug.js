// This module is served and loaded only when the FastAPI app is in development.
const MAX_ERRORS = 50;
const STATIC_PATHS = new Set([
  "/", "/login", "/signup", "/logout", "/app", "/app/books",
]);

function safePath() {
  // Only known, complete route shapes survive. Never keep query/hash or IDs.
  const path = window.location.pathname;
  if (STATIC_PATHS.has(path)) return path;
  if (/^\/app\/books\/[^/]+\/borrow$/.test(path)) {
    return "/app/books/[가림]/borrow";
  }
  if (/^\/app\/loans\/[^/]+\/return$/.test(path)) {
    return "/app/loans/[가림]/return";
  }
  return "/[가림]";
}

function safeError(error) {
  // Free-form messages, names, stacks, URLs and arbitrary rejection objects can
  // contain credentials or personal data. Classify without reading those fields.
  if (error instanceof TypeError) {
    return { kind: "TypeError", summary: "값의 형식이나 접근을 확인하세요." };
  }
  if (error instanceof ReferenceError) {
    return { kind: "ReferenceError", summary: "참조한 변수의 선언을 확인하세요." };
  }
  if (error instanceof SyntaxError) {
    return { kind: "SyntaxError", summary: "스크립트 문법을 확인하세요." };
  }
  if (error instanceof RangeError) {
    return { kind: "RangeError", summary: "값의 범위나 호출 깊이를 확인하세요." };
  }
  return { kind: "Error", summary: "브라우저에서 오류가 발생했습니다." };
}

class LibraryDebugTools extends HTMLElement {
  #errors = [];
  #subscriptions;
  #open = false;

  connectedCallback() {
    // Reconnection always releases the previous listeners first.
    this.#subscriptions?.abort();
    this.#subscriptions = new AbortController();
    const { signal } = this.#subscriptions;
    this.innerHTML = `
      <button type="button" class="debug-toggle" aria-label="개발 디버그 패널 열기"
          aria-expanded="false" aria-controls="library-debug-panel">
        <span aria-hidden="true">D</span><span class="debug-badge" hidden></span>
      </button>
      <section id="library-debug-panel" class="debug-panel" role="region"
          aria-labelledby="library-debug-title" hidden>
        <div class="debug-heading">
          <h2 id="library-debug-title">개발 디버그</h2>
          <button type="button" class="debug-close" aria-label="디버그 패널 닫기">닫기</button>
        </div>
        <span class="debug-mode">개발 모드 · FastAPI / Jinja2</span>
        <h3>현재 페이지</h3>
        <code class="debug-path"></code>
        <div class="debug-heading">
          <h3>브라우저 오류 <span class="debug-count" role="status" aria-live="polite"></span></h3>
          <button type="button" class="debug-clear">기록 지우기</button>
        </div>
        <p class="debug-empty">현재 문서에서 수집한 오류가 없습니다.</p>
        <ol class="debug-errors"></ol>
        <p class="debug-note">최근 50개 · 페이지 이동 시 초기화<br>
          오류 원문·스택·개인정보는 기록하지 않습니다. 서버 오류는 터미널에서 확인하세요.</p>
      </section>`;

    this.querySelector(".debug-toggle").addEventListener("click", () => {
      this.#setOpen(!this.#open);
    }, { signal });
    this.querySelector(".debug-close").addEventListener("click", () => {
      this.#setOpen(false);
    }, { signal });
    this.querySelector(".debug-clear").addEventListener("click", () => {
      this.#errors = [];
      this.#renderErrors();
    }, { signal });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && this.#open && !event.defaultPrevented) {
        this.#setOpen(false);
      }
    }, { signal });
    window.addEventListener("error", (event) => {
      this.#record("스크립트 오류", event.error);
    }, { signal });
    window.addEventListener("unhandledrejection", (event) => {
      this.#record("처리되지 않은 Promise", event.reason);
    }, { signal });
    window.addEventListener("popstate", () => this.#renderPath(), { signal });
    window.addEventListener("hashchange", () => this.#renderPath(), { signal });
    this.#setOpen(false, false);
    this.#renderPath();
    this.#renderErrors();
  }

  disconnectedCallback() {
    this.#subscriptions?.abort();
  }

  #setOpen(open, restoreFocus = true) {
    this.#open = open;
    const toggle = this.querySelector(".debug-toggle");
    this.querySelector(".debug-panel").hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", `개발 디버그 패널 ${open ? "닫기" : "열기"}`);
    if (open) {
      this.#renderPath();
      this.querySelector(".debug-close").focus();
    } else if (restoreFocus) {
      toggle.focus();
    }
  }

  #renderPath() {
    this.querySelector(".debug-path").textContent = safePath();
  }

  #record(source, error) {
    // Store only this sanitized projection; never retain the event or reason.
    this.#errors.unshift({
      time: new Date().toISOString(),
      source,
      path: safePath(),
      ...safeError(error),
    });
    this.#errors.length = Math.min(this.#errors.length, MAX_ERRORS);
    this.#renderErrors();
  }

  #renderErrors() {
    const count = this.#errors.length;
    this.querySelector(".debug-count").textContent = `${count}개`;
    const badge = this.querySelector(".debug-badge");
    badge.hidden = count === 0;
    badge.textContent = String(count);
    badge.setAttribute("aria-label", `오류 ${count}개`);
    this.querySelector(".debug-empty").hidden = count > 0;
    this.querySelector(".debug-errors").replaceChildren(...this.#errors.map((entry) => {
      const row = document.createElement("li");
      const time = document.createElement("time");
      time.dateTime = entry.time;
      time.textContent = new Date(entry.time).toLocaleTimeString("ko-KR", { hour12: false });
      const title = document.createElement("strong");
      title.textContent = `${entry.source} · ${entry.kind}`;
      const summary = document.createElement("p");
      summary.textContent = entry.summary;
      const path = document.createElement("code");
      path.textContent = entry.path;
      row.append(time, title, summary, path);
      return row;
    }));
  }
}

if (!customElements.get("library-debug-tools")) {
  customElements.define("library-debug-tools", LibraryDebugTools);
}
if (!document.querySelector("library-debug-tools")) {
  document.body.append(document.createElement("library-debug-tools"));
}
