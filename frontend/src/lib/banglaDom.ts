/**
 * Shows the whole page in Bangla, including text that arrives from the API.
 *
 * Pages keep English as their source text, and this translates what is on screen against
 * a reviewed catalogue. Anything not in the catalogue stays readable in English, and
 * resident reports and official alert wording are left exactly as written.
 */

export type Catalogue = Record<string, string>;

// A value already formatted in Bangla, such as a date, counts as one number.
const NUMBER = /[\u0980-\u09FF][\u0980-\u09FF\s.,:০-৯]*(?:\s?[AP]M(?:\sIST)?)?|\d+(?:[.,]\d+)*/g;
const BENGALI_DIGITS = "০১২৩৪৫৬৭৮৯";
const SKIPPED = "SCRIPT,STYLE,CODE,PRE,INPUT,TEXTAREA".split(",");
const ATTRIBUTES = ["placeholder", "aria-label", "title"];
const MACHINE_TEXT = /^[\w.+-]+@|https?:|[A-Z]{3,}-[A-Z0-9]+-|^[\d\s.,:/-]+[A-Za-z]{0,2}$/;

const seen = new WeakMap<Node, { original: string; shown: string }>();
const missing = new Set<string>();

export function bengaliDigits(text: string): string {
  return text.replace(/\d/g, (digit) => BENGALI_DIGITS[Number(digit)]);
}

function fill(template: string, numbers: string[]): string {
  let next = 0;
  return template.replace(/\{(n|\d)\}/g, (_, name: string) => {
    const value = name === "n" ? numbers[next++] : numbers[Number(name) - 1];
    return value ?? "";
  });
}

function lookup(text: string, catalogue: Catalogue): string | null {
  if (catalogue[text]) return catalogue[text];
  const numbers = text.match(NUMBER) ?? [];
  if (numbers.length) {
    const template = catalogue[text.replace(NUMBER, "{n}")];
    if (template) return fill(template, numbers);
  }
  return null;
}

function translateCore(text: string, catalogue: Catalogue): string | null {
  const direct = lookup(text, catalogue);
  if (direct) return direct;
  const ending = text.match(/[.:;,!?]$/)?.[0];
  if (ending) {
    const bare = lookup(text.slice(0, -1), catalogue);
    if (bare) return bare + (ending === "." ? "।" : ending);
  }
  // Long messages and "a · b · c" lines are built from pieces, so translate piece by piece.
  for (const pattern of [/\s·\s/, /(?<=[.!?])\s+/, /,\s/, /\s-\s/]) {
    const pieces = text.split(pattern);
    if (pieces.length > 1) {
      const parts = pieces.map((piece) => translateCore(piece, catalogue));
      if (parts.some(Boolean)) {
        const joiner = pattern.source.includes("·") ? " · " : pattern.source.startsWith(",") ? ", " : pattern.source.includes("-") ? " - " : " ";
        return parts.map((part, index) => part ?? pieces[index]).join(joiner);
      }
    }
  }
  return null;
}

export function translateText(text: string, catalogue: Catalogue): string {
  const core = text.replace(/\s+/g, " ").trim();
  if (!core || !/[A-Za-z0-9]/.test(core) || MACHINE_TEXT.test(core) && !/\d/.test(core.slice(0, 1))) {
    return text;
  }
  const translated = translateCore(core, catalogue);
  if (translated === null && /[A-Za-z]{2}/.test(core)) missing.add(core);
  const start = text.match(/^\s*/)?.[0] ?? "";
  const end = text.match(/\s*$/)?.[0] ?? "";
  const shown = (translated ?? core).replace(/\bAM\b/g, "পূর্বাহ্ণ").replace(/\bPM\b/g, "অপরাহ্ণ").replace(/\bmm\b/g, "মিমি").replace(/\bkm\b/g, "কিমি").replace(/\bkm\/h\b/g, "কিমি/ঘণ্টা").replace(/কিমি\/h\b/g, "কিমি/ঘণ্টা").replace(/\/decade\b/g, "/দশক").replace(/\bdays\b/g, "দিন").replace(/\bKolkata\b/g, "কলকাতা").replace(/\bAaboh\b/g, "আবহ");
  return start + bengaliDigits(shown) + end;
}

function isSkipped(element: Element | null): boolean {
  return !element || SKIPPED.includes(element.tagName) || Boolean(element.closest("[data-original-text]"));
}

function translateNode(node: Text, catalogue: Catalogue) {
  if (isSkipped(node.parentElement)) return;
  const known = seen.get(node);
  if (known && node.data === known.shown) return;
  const original = node.data;
  const shown = translateText(original, catalogue);
  seen.set(node, { original, shown });
  if (shown !== original) node.data = shown;
}

function translateAttributes(element: Element, catalogue: Catalogue) {
  for (const name of ATTRIBUTES) {
    const value = element.getAttribute(name);
    const key = `data-en-${name}`;
    if (value && element.getAttribute(key) === null) {
      const shown = translateText(value, catalogue);
      if (shown !== value) {
        element.setAttribute(key, value);
        element.setAttribute(name, shown);
      }
    }
  }
}

function walk(root: Node, catalogue: Catalogue) {
  if (root.nodeType === Node.TEXT_NODE) {
    translateNode(root as Text, catalogue);
    return;
  }
  if (root.nodeType !== Node.ELEMENT_NODE) return;
  const element = root as Element;
  if (isSkipped(element)) return;
  translateAttributes(element, catalogue);
  element.querySelectorAll(`[${ATTRIBUTES.join("],[")}]`).forEach((child) => {
    if (!isSkipped(child)) translateAttributes(child, catalogue);
  });
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) translateNode(node as Text, catalogue);
}

function restore(root: Element) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const known = seen.get(node);
    if (known && (node as Text).data === known.shown) (node as Text).data = known.original;
    seen.delete(node);
  }
  for (const name of ATTRIBUTES) {
    root.querySelectorAll(`[data-en-${name}]`).forEach((element) => {
      element.setAttribute(name, element.getAttribute(`data-en-${name}`) ?? "");
      element.removeAttribute(`data-en-${name}`);
    });
  }
}

/** Starts translating the page and returns a function that puts the English back. */
export function startBangla(catalogue: Catalogue): () => void {
  const root = document.body;
  walk(root, catalogue);
  const observer = new MutationObserver((changes) => {
    for (const change of changes) {
      if (change.type === "characterData") translateNode(change.target as Text, catalogue);
      change.addedNodes.forEach((node) => walk(node, catalogue));
    }
  });
  observer.observe(root, { subtree: true, childList: true, characterData: true });
  (window as unknown as { __banglaMissing?: Set<string> }).__banglaMissing = missing;
  return () => {
    observer.disconnect();
    restore(root);
  };
}
