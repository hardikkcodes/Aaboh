import { createContext, useContext } from "react";

export type Language = "en" | "bn";

type Params = Record<string, string | number>;

/** English text is the key, so anything untranslated stays readable. */
const BENGALI: Record<string, string> = {
  Today: "আজ",
  Learn: "জানুন",
  "Tomorrow's rain forecast": "আগামীকালের বৃষ্টির পূর্বাভাস",
  "UV index": "ইউভি সূচক",
  "tip.high_uv": "ইউভি সূচক {uv} পর্যন্ত উঠবে। দুপুরে ছায়া, টুপি ও সানস্ক্রিন ব্যবহার করুন।",
  "Next 12 hours": "পরের ১২ ঘণ্টা",
  "Cool spots": "ঠান্ডা জায়গা",
  "Model status": "মডেলের অবস্থা",
  "Cleanest air: {start} to {end}": "সবচেয়ে পরিষ্কার বাতাস: {start} থেকে {end}",
  "Live map": "লাইভ মানচিত্র",
  Report: "জানান",
  Routes: "রুট",
  "My routes": "আমার রুট",
  Plan: "পরিকল্পনা",
  "Week planner": "সাপ্তাহিক পরিকল্পনা",
  Safety: "নিরাপত্তা",
  Alerts: "সতর্কতা",
  Community: "কমিউনিটি",
  Insights: "বিশ্লেষণ",
  Overview: "সারসংক্ষেপ",
  Weather: "আবহাওয়া",
  "Official alerts": "সরকারি সতর্কতা",
  "Heat & environment": "গরম ও পরিবেশ",
  Rainfall: "বৃষ্টিপাত",
  "Air quality": "বাতাসের মান",
  Climate: "জলবায়ু",
  Methodology: "পদ্ধতি",
  More: "আরও",
  "Log in": "লগ ইন",
  "Log out": "লগ আউট",
  "Create account": "অ্যাকাউন্ট তৈরি করুন",
  Notifications: "বিজ্ঞপ্তি",
  "Today in {place}": "আজ {place}-এ",
  "Rain, next 2 hours": "পরের ২ ঘণ্টায় বৃষ্টি",
  "Feels like, today's peak": "আজ সর্বোচ্চ অনুভূত গরম",
  "Nearest station AQI": "নিকটতম স্টেশনের AQI",
  "Reports nearby": "কাছাকাছি রিপোর্ট",
  "Official warnings": "সরকারি সতর্কতা",
  "Not available": "তথ্য নেই",
  "Rain likely around {time}": "প্রায় {time}-এ বৃষ্টির সম্ভাবনা",
  "No rain signal in the next 24 hours": "পরের ২৪ ঘণ্টায় বৃষ্টির ইঙ্গিত নেই",
  "Best time outdoors: {start} to {end}": "বাইরে যাওয়ার ভালো সময়: {start} থেকে {end}",
  "No clear dry, cooler window today": "আজ শুকনো ও ঠান্ডা সময় স্পষ্ট নয়",
  "What to do today": "আজ কী করবেন",
  "No strong signal right now. This is not a guarantee of safety.":
    "এই মুহূর্তে কোনো জোরালো ইঙ্গিত নেই। এটি নিরাপত্তার নিশ্চয়তা নয়।",
  "The forecast may be out of date.": "পূর্বাভাস পুরোনো হতে পারে।",
  "No forecast is available right now.": "এখন কোনো পূর্বাভাস নেই।",
  "Change place": "জায়গা বদলান",
  "Use my location": "আমার অবস্থান ব্যবহার করুন",
  "Finding your location…": "আপনার অবস্থান খোঁজা হচ্ছে…",
  "Update to my location": "আমার অবস্থানে আপডেট করুন",
  Share: "শেয়ার করুন",
  "Copied": "কপি হয়েছে",
  "What residents are reporting now": "বাসিন্দারা এখন কী জানাচ্ছেন",
  "Report now": "এখনই জানান",
  "Report what you see": "যা দেখছেন জানান",
  "What is it?": "কী হয়েছে?",
  "Where?": "কোথায়?",
  "How deep?": "কত গভীর?",
  "What can get through?": "কী যেতে পারবে?",
  "Send report": "রিপোর্ট পাঠান",
  Waterlogging: "জল জমা",
  "Power cut": "বিদ্যুৎ বিভ্রাট",
  "Fallen tree": "গাছ পড়েছে",
  "Blocked road": "রাস্তা বন্ধ",
  "Stagnant water": "জমে থাকা জল",
  "Transport disruption": "যানবাহনে সমস্যা",
  Ankle: "গোড়ালি",
  Knee: "হাঁটু",
  Waist: "কোমর",
  "Above waist": "কোমরের ওপরে",
  "Cars pass": "গাড়ি যাচ্ছে",
  "Two-wheelers pass": "দু-চাকা যাচ্ছে",
  "Walking only": "শুধু হেঁটে",
  "Not passable": "যাওয়া যাচ্ছে না",
  "Still there": "এখনও আছে",
  Cleared: "ঠিক হয়ে গেছে",
  "Looks wrong": "ভুল মনে হচ্ছে",
  All: "সব",
  "Accurate to about {metres} m": "প্রায় {metres} মিটার পর্যন্ত নির্ভুল",
  "This location is rough. Tap the map to correct it.":
    "এই অবস্থানটি আনুমানিক। মানচিত্রে ট্যাপ করে ঠিক করুন।",
  "The location is public. Mark the road, not a home.":
    "অবস্থানটি সর্বজনীন। রাস্তা চিহ্নিত করুন, বাড়ি নয়।",
  "For immediate danger, call 112.": "তাৎক্ষণিক বিপদে ১১২ নম্বরে ফোন করুন।",
  Good: "ভালো",
  Fair: "মোটামুটি",
  Poor: "খারাপ",
  "Your week": "আপনার সপ্তাহ",
  "Stay ready": "প্রস্তুত থাকুন",
  "Emergency numbers": "জরুরি নম্বর",
  "Save route": "রুট সংরক্ষণ করুন",
  "No active reports along this route. That does not mean the road is clear.":
    "এই রুটে কোনো সক্রিয় রিপোর্ট নেই। এর মানে রাস্তা পরিষ্কার নয়।",
  "tip.official_alert": "এই এলাকায় {count}টি সরকারি সতর্কতা আছে। মূল বুলেটিন পড়ুন।",
  "tip.heavy_rain_soon": "পরের ২ ঘণ্টায় প্রায় {mm} মিমি ভারী বৃষ্টির পূর্বাভাস। হাতে সময় নিয়ে বেরোন।",
  "tip.carry_umbrella": "পরে বৃষ্টির সম্ভাবনা আছে। ছাতা সঙ্গে রাখুন।",
  "tip.reports_nearby": "কাছাকাছি {count}টি সক্রিয় রিপোর্ট আছে। বেরোনোর আগে লাইভ মানচিত্র দেখুন।",
  "tip.heat_caution": "আজ অনুভূত গরম {index}°C পর্যন্ত। জল খান, দুপুরে পরিশ্রম কমান।",
  "tip.heat_warning": "আজ অনুভূত গরম {index}°C পর্যন্ত। জল খান, দুপুরে পরিশ্রম কমান।",
  "tip.warm_night": "রাতে গরম থাকবে, প্রায় {low}°C। বয়স্ক আত্মীয়দের খোঁজ নিন।",
  "tip.poor_air": "নিকটতম স্টেশনের AQI {aqi}। সংবেদনশীল ব্যক্তিরা বাইরে পরিশ্রম কমাতে পারেন।",
};

const LanguageContext = createContext<{ lang: Language; setLang: (lang: Language) => void }>({
  lang: "en",
  setLang: () => undefined,
});

export const LanguageContextProvider = LanguageContext.Provider;

export function translate(lang: Language, key: string, params?: Params, fallback?: string): string {
  const template = (lang === "bn" ? BENGALI[key] : undefined) ?? fallback ?? key;
  return template.replace(/\{(\w+)\}/g, (match, name: string) => String(params?.[name] ?? match));
}

export function useT() {
  const { lang, setLang } = useContext(LanguageContext);
  return {
    lang,
    setLang,
    t: (key: string, params?: Params, fallback?: string) => translate(lang, key, params, fallback),
  };
}
