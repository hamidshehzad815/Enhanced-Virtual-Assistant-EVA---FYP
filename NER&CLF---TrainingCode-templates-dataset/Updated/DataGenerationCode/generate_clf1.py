"""
Generate CLF1 (Input Type Classification) Dataset
===================================================
Produces Updated/Datasets/clf1_train.json  (90%)
         Updated/Datasets/clf1_test.json   (10%)

Strategy:
  - command / multiple_command: already sufficient in old dataset — copy as-is
  - out_of_scope / general: copy old + generate extra
  - confirmation: copy old + add negative confirmations ("no", "nope", "cancel")
  - help: 62 examples -> 500 target — generate from scratch with rich templates

CLF1 classes + targets (plan Phase 5):
  command         : 6500  (copy from old)
  multiple_command: 1200  (copy 1000 from old + generate 200 more)
  out_of_scope    : 800   (copy 748 + 52 new)
  general         : 600   (copy 348 + 252 new)
  confirmation    : 600   (copy 323 + 277 new)
  help            : 500   (copy 62  + 438 new)
  TOTAL           : 10200 (trimmed to produce nice train/test split)
"""

import sys, os, json, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Templates'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'SlotArrays'))

SEED = 17
rng  = random.Random(SEED)

# ── Help templates ────────────────────────────────────────────────────────────
HELP_TEXTS = [
    "help", "help me", "help me out", "help please", "help pls",
    "i need help", "need some help", "can you help me", "can u help me",
    "i need assistance", "assist me please",
    "how does this work", "how do you work", "how does eva work",
    "what can you do", "what can u do", "what are your features",
    "what can eva do", "tell me what you can do",
    "what are you capable of", "what r u capable of",
    "what is eva", "who are you", "what do you do",
    "explain yourself", "explain what you can do",
    "show me what you can do", "show me your features",
    "guide me", "guide me please", "guide me through this",
    "can you guide me", "i need a guide",
    "how to use this", "how do i use eva", "how do i use this app",
    "how can i use you", "how should i use you",
    "teach me how to use this", "can you teach me",
    "i'm lost", "i'm confused", "i am lost", "i am confused",
    "i don't know what to do", "i dont know what to do",
    "what commands do you support", "what commands are available",
    "list your commands", "show me commands",
    "what can i ask you", "what can i say to you",
    "give me examples", "show me some examples",
    "can you give me examples", "what kind of things can i ask",
    "what kinds of requests do you handle",
    "do you support reminders", "can you set reminders",
    "do you support tasks", "can you manage tasks",
    "do you support scheduling", "can you schedule things",
    "do you support learning", "can you help me learn",
    "can you create roadmaps", "do you have learning features",
    "what scheduling features do you have",
    "tell me about your features", "describe your features",
    "i want to know what you can do",
    "explain your capabilities",
    "what else can you do",
    "is there anything else you can do",
    "what other things can you help with",
    "can you help me with more than just tasks",
    "what are all the things you can do",
    "tell me everything you can do",
    "show everything", "tell me all features",
    "how do i add a task", "how do i schedule a task",
    "how do i delete a task", "how do i update a task",
    "how do i create a learning plan", "how do i start learning",
    "how do i see my tasks", "how do i check my schedule",
    "can you help me schedule", "can you help me learn programming",
    "what programming languages do you support",
    "i need help with eva", "help with eva",
    "help me understand", "help me understand eva",
    "i am new here", "i just started using this",
    "first time using this", "new user help",
    "what should i do first", "where do i start",
    "how do i get started", "getting started",
    "help getting started", "need help getting started",
    "tutorial please", "show me a tutorial",
    "do you have a tutorial", "can you walk me through this",
    "walk me through it", "walk me through eva",
    "step by step guide", "give me a step by step",
    "beginners guide", "guide for beginners",
]

# ── Confirmation templates ────────────────────────────────────────────────────
EXTRA_CONFIRMATION_TEXTS = [
    # positive
    "yes", "yeah", "yep", "yup", "sure", "ok", "okay", "alright",
    "of course", "definitely", "absolutely", "correct", "right",
    "exactly", "that's right", "that is right", "confirmed",
    "go ahead", "do it", "proceed", "sounds good", "sounds great",
    "that works", "fine", "affirmative", "roger",
    "ya", "ye", "yea", "uh huh", "uh-huh", "mhm",
    "please do", "please proceed", "yes please", "yes do it",
    "confirm", "i confirm", "i agree", "agreed",
    # negative
    "no", "nope", "nah", "no thanks", "no thank you",
    "cancel", "cancel it", "don't do it", "stop",
    "never mind", "nevermind", "never mind that",
    "actually no", "on second thought no",
    "don't", "please don't", "hold on",
    "wait", "wait no", "not now", "not yet",
    "discard", "discard it", "forget it", "forget that",
    "abort", "abort that", "undo", "undo that",
]

# ── General (greeting / chit-chat) templates ─────────────────────────────────
EXTRA_GENERAL_TEXTS = [
    "hi", "hello", "hey", "hey there", "hi there",
    "good morning", "good afternoon", "good evening", "good night",
    "morning", "afternoon", "evening",
    "howdy", "greetings", "salutations",
    "hi eva", "hello eva", "hey eva",
    "sup", "whats up", "what's up", "wassup",
    "how are you", "how r u", "how are you doing",
    "how's it going", "how's everything",
    "i'm doing well", "i am doing well", "doing good",
    "thanks", "thank you", "thank u", "thx", "ty",
    "thanks a lot", "thank you so much", "many thanks",
    "cheers", "appreciate it", "appreciated",
    "great job", "well done", "good job", "nice",
    "awesome", "excellent", "fantastic", "perfect",
    "bye", "goodbye", "see you", "see ya", "later",
    "talk to you later", "ttyl", "take care",
    "ok cool", "cool", "nice work", "good work",
    "that's cool", "that's great", "that's awesome",
    "wow", "amazing", "impressive",
    "you're great", "you're awesome", "you're helpful",
    "you are great", "you are awesome",
    "i like you", "i love you eva",
    "tell me a joke", "say something funny",
    "what's the weather", "what is the weather",
    "what time is it", "what's the time",
    "who made you", "who created you",
    "are you a bot", "are you an AI", "are you real",
    "what's your name", "what is your name",
    "do you have feelings", "do you understand me",
    "you're smart", "smart bot",
]

# ── Out-of-scope templates ────────────────────────────────────────────────────
EXTRA_OOS_TEXTS = [
    "order a pizza", "book a flight", "book a hotel",
    "play music", "play a song", "play something",
    "call someone", "call my mom", "make a call",
    "send an email", "send a message to someone",
    "search the web", "search google for me",
    "what's the news", "show me news",
    "what are stocks doing", "check stock prices",
    "translate this to french", "translate hello to urdu",
    "do my homework", "write an essay for me",
    "write code for me", "fix my code",
    "what is the capital of france", "what is 2+2",
    "solve this math problem", "calculate this for me",
    "draw something", "create an image",
    "set an alarm", "set a timer for 5 minutes",
    "turn off lights", "open netflix",
    "navigate to downtown", "get directions",
    "how do i cook pasta", "give me a recipe",
    "can you shop for me", "buy something for me",
    "find a restaurant near me", "recommend a movie",
    "who won the game", "what are the scores",
    "check my email", "read my messages",
    "post on instagram", "post on twitter",
    "generate a password", "what is my ip address",
    "tell me about history", "who was einstein",
    "explain quantum physics", "what is gravity",
    "can you drive me", "book an uber",
    "can you pay my bills", "make a payment",
]

# ── Bare / entity-less command templates ─────────────────────────────────────
# CLF1 was misclassifying short imperatives with a generic object and no real
# entity (e.g. "add a task", "delete a task", "show a task", "update a task").
# The old command bucket has entity-rich phrasings but almost none of these
# bare forms, so the model was unsure. These are all unambiguously `command`.
EXTRA_COMMAND_TEXTS = [
    # add / create / schedule
    "add a task", "add task", "add a new task", "add a task please",
    "add a task for me", "add something", "add a reminder", "add a new reminder",
    "create a task", "create task", "create a new task", "make a task",
    "set a task", "new task", "schedule a task", "schedule task",
    "schedule something", "can you add a task", "please add a task",
    "i want to add a task", "i need to add a task", "add a task for tomorrow",
    # delete / remove / cancel
    "delete a task", "delete task", "delete a task please", "delete my task",
    "delete one task", "delete one of my tasks", "delete something",
    "delete a scheduled task", "remove a task", "remove task", "remove my task",
    "remove something", "cancel a task", "cancel task", "can you delete a task",
    "please delete a task", "i want to delete a task", "i need to delete a task",
    # show / view / list
    "show a task", "show task", "show my tasks", "show tasks", "show me a task",
    "show me my tasks", "show all tasks", "show something", "view a task",
    "view tasks", "view my tasks", "list tasks", "list my tasks", "see my tasks",
    "display my tasks", "check my tasks", "what are my tasks",
    "can you show my tasks", "show me the tasks",
    # update / edit / reschedule
    "update a task", "update task", "update my task", "update my tasks",
    "update something", "update a task please", "update a scheduled task",
    "edit a task", "edit task", "edit my task", "change a task", "change my task",
    "modify a task", "reschedule a task", "reschedule task", "reschedule my task",
    "can you update a task", "i want to update a task", "i need to update a task",
    # learning (still input-type `command`)
    "create a roadmap", "create roadmap", "make a roadmap", "build a roadmap",
    "create a plan", "create a learning plan", "make a learning plan",
    "start a roadmap", "start learning", "add a learning plan",
    "delete a roadmap", "delete my roadmap", "remove a roadmap",
    "update my roadmap", "update a roadmap",
]

# ── Multiple command ──────────────────────────────────────────────────────────
EXTRA_MULTIPLE_COMMAND_TEXTS = [
    "add math exam on monday and also add physics exam on tuesday",
    "schedule biology lab on friday and delete chemistry test on thursday",
    "add fyp meeting on wednesday and show my tasks for this week",
    "delete all done tasks and show pending ones",
    "add cs project on monday at 2pm and also add db quiz on tuesday",
    "reschedule math exam to friday and mark the physics lab as done",
    "add two tasks math and physics both on monday",
    "create a python roadmap and also add fyp meeting tomorrow",
    "add phy exam tomorrow and delete the old one from monday",
    "show tasks for monday and also add a new one for tuesday",
    "delete cs lab and also add a new one next week",
    "mark phy exam as done and add chemistry exam for friday",
    "update math exam time to 3pm and add study session tonight",
    "add biology homework and also remind me about cs lab",
    "delete done tasks and schedule new ones for next week",
    "create java roadmap and delete my old python plan",
    "pause python learning and start javascript learning",
    "add phy exam on monday and mark last week tasks as done",
    "schedule two exams one on monday and one on tuesday",
    "add exam and show all my tasks",
    "reschedule and also add a new task",
    "delete old tasks and add new ones",
    "add cs assignment on tuesday and update priority of phy exam to high",
    "mark lab report done and add a new submission deadline",
    "show tasks for tomorrow and add a reminder for friday",
    "delete phy exam and also delete chem exam",
    "add three tasks monday tuesday and wednesday",
]


def _load_old_clf1():
    old_path = os.path.join(
        os.path.dirname(__file__), '..', '..',
        'Current(old)', 'DataSets', 'CLF1CompleteDataSet.json'
    )
    with open(old_path, encoding='utf-8') as f:
        return json.load(f)


def _build_clf1_examples(texts, intent):
    return [{"text": t, "intent": intent} for t in texts]


def run():
    old_data = _load_old_clf1()

    # Bucket by intent
    from collections import defaultdict
    old_by_intent = defaultdict(list)
    for ex in old_data:
        old_by_intent[ex['intent']].append(ex)

    all_examples = []

    # command — copy all 6500 + inject bare/entity-less imperatives
    all_examples.extend(old_by_intent['command'])
    extra_cmd = _build_clf1_examples(EXTRA_COMMAND_TEXTS, 'command')
    # ~90 unique bare-command forms; cycle to give them enough weight against
    # the 6500 entity-rich command examples (same approach used for `help`).
    generic_cmd_target = 300
    cycled_cmd = []
    while len(cycled_cmd) < generic_cmd_target:
        shuffled_cmd = list(extra_cmd)
        rng.shuffle(shuffled_cmd)
        cycled_cmd.extend(shuffled_cmd)
    all_examples.extend(cycled_cmd[:generic_cmd_target])

    # multiple_command — 1000 old + 200 new synthetic
    all_examples.extend(old_by_intent['multiple_command'])
    extra_mc = _build_clf1_examples(EXTRA_MULTIPLE_COMMAND_TEXTS, 'multiple_command')
    rng.shuffle(extra_mc)
    all_examples.extend(extra_mc[:200])

    # out_of_scope — 748 old + up to 52 new
    all_examples.extend(old_by_intent['out_of_scope'])
    extra_oos = _build_clf1_examples(EXTRA_OOS_TEXTS, 'out_of_scope')
    rng.shuffle(extra_oos)
    all_examples.extend(extra_oos[:52])

    # general — 348 old + 252 new
    all_examples.extend(old_by_intent['general'])
    extra_gen = _build_clf1_examples(EXTRA_GENERAL_TEXTS, 'general')
    rng.shuffle(extra_gen)
    all_examples.extend(extra_gen[:252])

    # confirmation — 323 old + 277 new
    all_examples.extend(old_by_intent['confirmation'])
    extra_conf = _build_clf1_examples(EXTRA_CONFIRMATION_TEXTS, 'confirmation')
    rng.shuffle(extra_conf)
    all_examples.extend(extra_conf[:277])

    # help — 62 old + 438 new (use all HELP_TEXTS we have; sample if needed)
    all_examples.extend(old_by_intent['help'])
    help_examples = _build_clf1_examples(HELP_TEXTS, 'help')
    rng.shuffle(help_examples)
    # HELP_TEXTS has ~130 unique strings; cycle to reach 438
    needed = 438
    cycled_help = []
    while len(cycled_help) < needed:
        shuffled_copy = list(help_examples)
        rng.shuffle(shuffled_copy)
        cycled_help.extend(shuffled_copy)
    all_examples.extend(cycled_help[:needed])

    rng.shuffle(all_examples)

    split = int(len(all_examples) * 0.9)
    train = all_examples[:split]
    test  = all_examples[split:]

    out_dir = os.path.join(os.path.dirname(__file__), '..', 'Datasets')
    os.makedirs(out_dir, exist_ok=True)

    train_path = os.path.join(out_dir, 'clf1_train.json')
    test_path  = os.path.join(out_dir, 'clf1_test.json')

    with open(train_path, 'w', encoding='utf-8') as f:
        json.dump(train, f, indent=2, ensure_ascii=False)
    with open(test_path, 'w', encoding='utf-8') as f:
        json.dump(test, f, indent=2, ensure_ascii=False)

    print(f"[clf1] Done.")
    print(f"  Train : {len(train)} -> {train_path}")
    print(f"  Test  : {len(test)}  -> {test_path}")

    from collections import Counter
    dist = Counter(ex['intent'] for ex in train)
    print("\n[clf1] Class distribution in train split:")
    for intent, cnt in sorted(dist.items()):
        print(f"  {intent:20s}: {cnt}")

if __name__ == '__main__':
    run()
