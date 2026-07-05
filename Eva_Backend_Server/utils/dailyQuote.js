/**
 * Deterministic "quote of the day" for the Collaboration screen.
 *
 * The same quote is returned for the whole calendar day (in the user's
 * timezone), and the list rotates one-per-day so every quote is shown once
 * before any repeats (~one full cycle = QUOTES.length days). No storage or
 * randomness needed — the index is derived purely from the local date.
 *
 * Quotes are interleaved across categories (study / growth / friendship /
 * motivation) so consecutive days feel varied rather than grouped.
 */

const { normalizeTimezone } = require("./timezone");

const QUOTES = [
  { text: "The only thing that interferes with my learning is my education.", author: "Albert Einstein" },
  { text: "The only way to do great work is to love what you do.", author: "Steve Jobs" },
  { text: "Alone we can do so little; together we can do so much.", author: "Helen Keller" },
  { text: "The secret of change is to focus all of your energy not on fighting the old, but on building the new.", author: "Socrates" },
  { text: "Live as if you were to die tomorrow. Learn as if you were to live forever.", author: "Mahatma Gandhi" },
  { text: "Believe you can and you're halfway there.", author: "Theodore Roosevelt" },
  { text: "Friendship is born at that moment when one person says to another, 'What! You too? I thought I was the only one.'", author: "C.S. Lewis" },
  { text: "Don't let yesterday take up too much of today.", author: "Will Rogers" },
  { text: "Education is the most powerful weapon which you can use to change the world.", author: "Nelson Mandela" },
  { text: "It always seems impossible until it's done.", author: "Nelson Mandela" },
  { text: "If you want to go fast, go alone. If you want to go far, go together.", author: "African Proverb" },
  { text: "Start where you are. Use what you have. Do what you can.", author: "Arthur Ashe" },
  { text: "The beautiful thing about learning is that nobody can take it away from you.", author: "B.B. King" },
  { text: "You are never too old to set another goal or to dream a new dream.", author: "C.S. Lewis" },
  { text: "No one can whistle a symphony. It takes a whole orchestra to play it.", author: "H.E. Luccock" },
  { text: "The only impossible journey is the one you never begin.", author: "Tony Robbins" },
  { text: "Learning never exhausts the mind.", author: "Leonardo da Vinci" },
  { text: "What you get by achieving your goals is not as important as what you become.", author: "Zig Ziglar" },
  { text: "The greatest gift of life is friendship, and I have received it.", author: "Hubert H. Humphrey" },
  { text: "It's not whether you get knocked down, it's whether you get up.", author: "Vince Lombardi" },
  { text: "You don't have to be great to start, but you have to start to be great.", author: "Zig Ziglar" },
  { text: "The secret of getting ahead is getting started.", author: "Mark Twain" },
  { text: "A friend is someone who gives you total freedom to be yourself.", author: "Jim Morrison" },
  { text: "Make today so awesome that yesterday gets jealous.", author: "Unknown" },
  { text: "Success is the sum of small efforts repeated day in and day out.", author: "Robert Collier" },
  { text: "Don't watch the clock; do what it does. Keep going.", author: "Sam Levenson" },
  { text: "We are all just walking each other home.", author: "Ram Dass" },
  { text: "It does not matter how slowly you go as long as you do not stop.", author: "Confucius" },
  { text: "Small daily improvements over time lead to stunning results.", author: "Robin Sharma" },
  { text: "The most beautiful discovery true friends make is that they can grow separately without growing apart.", author: "Elizabeth Foley" },
  { text: "The mind is not a vessel to be filled, but a fire to be kindled.", author: "Plutarch" },
  { text: "Success is not final, failure is not fatal: it is the courage to continue that counts.", author: "Winston Churchill" },
  { text: "A real friend is one who walks in when the rest of the world walks out.", author: "Walter Winchell" },
  { text: "The expert in anything was once a beginner.", author: "Helen Hayes" },
  { text: "Push yourself, because no one else is going to do it for you.", author: "Anonymous" },
  { text: "Friendship doubles your joys and divides your sorrows.", author: "Unknown" },
  { text: "Study hard, for the well is deep and our brains are shallow.", author: "Anonymous" },
  { text: "Your limitation—it's only your imagination.", author: "Anonymous" },
  { text: "Knowledge is power. Information is liberating. Education is the premise of progress.", author: "Kofi Annan" },
  { text: "The best time to plant a tree was 20 years ago. The second best time is now.", author: "Chinese Proverb" },
];

/**
 * Whole-day number for the given timezone's current local date
 * (days since the Unix epoch). Stable for the entire local day.
 */
const localDayNumber = (timezoneValue) => {
  const timezone = normalizeTimezone(timezoneValue);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());

  const map = {};
  parts.forEach((part) => {
    if (part.type !== "literal") {
      map[part.type] = part.value;
    }
  });

  const utcMidnight = Date.UTC(
    Number.parseInt(map.year, 10),
    Number.parseInt(map.month, 10) - 1,
    Number.parseInt(map.day, 10),
  );

  return Math.floor(utcMidnight / 86400000);
};

/**
 * Pick the quote for today in the user's timezone.
 * @param {string} [timezoneValue] IANA timezone (defaults handled by normalizeTimezone).
 * @returns {{ text: string, author: string }}
 */
const getDailyQuote = (timezoneValue) => {
  const count = QUOTES.length;
  const index = ((localDayNumber(timezoneValue) % count) + count) % count;
  return QUOTES[index];
};

module.exports = {
  QUOTES,
  getDailyQuote,
};
