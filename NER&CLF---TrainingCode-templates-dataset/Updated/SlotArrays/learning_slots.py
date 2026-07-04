"""
Learning Slot Value Arrays
===========================
Phase 2: TOPICS split into SUPPORTED_TOPICS and UNSUPPORTED_TOPICS.
Added casual/abbreviated spellings for start_dates and durations.
Subtopic joined combos intentionally omitted (app supports 1 subtopic only).

Import these in DataGenerationCode scripts.
"""

# ── SUPPORTED TOPICS (Phase 2 split) ─────────────────────────────────────────
# Only these map to actual EVA roadmap functionality.
SUPPORTED_TOPICS = [
    # Programming Languages
    "Python", "JavaScript", "TypeScript", "Java", "C#",
    "C++", "Go", "Rust", "PHP", "Kotlin", "Swift",
    "Ruby", "Dart", "C",
    # Databases
    "Oracle", "MySQL", "Microsoft SQL Server",
    "PostgreSQL", "MongoDB", "SQL",
    # Aliases - Languages
    "golang", "js", "ts", "cpp", "py", "c sharp",
    "c plus plus", "javascript", "typescript",
    # Aliases - Databases
    "mongo", "postgres", "mssql", "postgre",
    "sql server", "my sql", "mongo db",
]

# ── UNSUPPORTED TOPICS (Phase 2 split) ───────────────────────────────────────
# EVA responds "not supported yet" — but NER must still extract the entity.
UNSUPPORTED_TOPICS = [
    # Programming Languages
    "Scala", "Haskell", "Elixir", "Lua", "R",
    "Julia", "Perl", "Bash", "Shell", "Groovy",
    "Clojure", "Assembly", "COBOL", "Fortran",
    "Nim", "Zig", "Crystal", "F#", "OCaml",
    "MATLAB", "Prolog", "Lisp", "Erlang",
    # Databases
    "Redis", "Cassandra", "SQLite", "MariaDB",
    "CouchDB", "DynamoDB", "Neo4j", "InfluxDB",
    "Elasticsearch", "Firebase", "Supabase",
    "Firestore", "PlanetScale", "Turso",
    # ML / DL / AI
    "Machine Learning", "Deep Learning", "Artificial Intelligence",
    "Neural Networks", "Computer Vision", "NLP",
    "Natural Language Processing", "Reinforcement Learning",
    "Data Science", "MLOps", "LLMs",
    "Large Language Models", "Generative AI",
    "ML", "DL", "AI", "CV", "RL", "data sci",
    "machine learning", "deep learning",
    "artificial intelligence", "neural network",
    # Backend Frameworks
    "Node.js", "Express.js", "Django", "Flask", "FastAPI",
    "Spring Boot", "Laravel", "Ruby on Rails",
    "ASP.NET", "NestJS", "Hono", "Fiber",
    "Gin", "Echo", "Actix", "Axum",
    "node", "nodejs", "express", "expressjs",
    "django", "flask", "fastapi", "spring",
    "laravel", "rails", "nestjs", "nest",
    "asp.net", "dotnet", "dot net",
    # Frontend Frameworks
    "React", "Vue.js", "Angular", "Svelte",
    "Next.js", "Nuxt.js", "Remix", "Astro",
    "React Native", "Flutter",
    "react", "reactjs", "react.js",
    "vue", "vuejs", "angular", "svelte",
    "nextjs", "next", "nuxt", "nuxtjs",
    "remix", "astro", "react native", "flutter",
    # DevOps / Cloud
    "Docker", "Kubernetes", "AWS", "Azure",
    "Google Cloud", "Terraform", "Ansible",
    "Jenkins", "GitHub Actions", "Linux",
    "Nginx", "CI/CD",
    "k8s", "kubernetes", "aws",
    "azure", "gcp", "google cloud", "terraform",
    "ansible", "jenkins", "linux", "nginx",
    "ci cd", "cicd", "devops",
    # Mobile
    "Android Development", "iOS Development", "Xamarin",
    "android", "ios", "mobile development",
    "mobile dev", "xamarin",
    # Data / Analytics
    "Data Analysis", "Data Engineering",
    "Power BI", "Tableau", "Pandas",
    "NumPy", "Apache Spark", "Hadoop",
    "data analysis", "data engineering",
    "powerbi", "power bi", "tableau",
    "pandas", "numpy", "spark", "hadoop",
    # Cybersecurity
    "Cybersecurity", "Ethical Hacking",
    "Penetration Testing", "Network Security", "Cryptography",
    "cyber security", "ethical hacking",
    "pen testing", "pentest", "infosec",
    "network security", "cryptography",
    # Blockchain / Web3
    "Blockchain", "Solidity", "Web3",
    "Smart Contracts", "Ethereum",
    "blockchain", "solidity", "web3",
    "smart contracts", "ethereum", "crypto dev",
    # Game Dev
    "Game Development", "Unity", "Unreal Engine",
    "Godot", "OpenGL",
    "game dev", "game development",
    "unity", "unreal", "godot", "opengl",
    # System Design / CS Fundamentals
    "System Design", "Data Structures",
    "Algorithms", "Operating Systems",
    "Computer Networks", "Discrete Mathematics",
    "Compiler Design",
    "system design", "dsa", "data structures",
    "algorithms", "os", "operating systems",
    "computer networks", "networking",
    "discrete math", "compilers",
]

# Combined list for scripts that don't need to distinguish
TOPICS = SUPPORTED_TOPICS + UNSUPPORTED_TOPICS

# ── SUBTOPICS ─────────────────────────────────────────────────────────────────
SUBTOPICS = [

    # ── Level-based ─────────────────────────────────────────
    "basics", "beginner", "fundamentals", "intro", "introduction",
    "intermediate", "mid level", "mid-level",
    "advanced", "expert", "pro", "master",

    # ── Variables and Data Types ─────────────────────────────
    "variables and data types", "variables", "data types",
    "variables and constants", "constants",

    # ── Control Flow ─────────────────────────────────────────
    "control flow", "conditionals", "if else",
    "if statements", "switch statements", "branching",

    # ── Loops ────────────────────────────────────────────────
    "loops", "for loop", "while loop", "iteration",
    "looping", "for loops", "while loops",

    # ── Functions / Methods ──────────────────────────────────
    "functions", "methods", "functions methods",
    "functions and closures", "closures",
    "lambdas", "higher order functions",
    "lambda functions", "higher-order functions",

    # ── Arrays / Collections ─────────────────────────────────
    "arrays", "arrays and strings", "arrays and collections",
    "arrays and hashes", "arrays and tuples",
    "arrays slices maps", "collections",
    "collections lists maps sets", "lists",
    "lists tuples dictionaries sets", "tuples",
    "maps", "sets", "hashes", "slices",
    "collections framework",

    # ── Strings ──────────────────────────────────────────────
    "strings", "strings and formatting",
    "strings and runes", "string manipulation",
    "string methods", "string functions",

    # ── OOP ──────────────────────────────────────────────────
    "oop", "object oriented programming",
    "oop concepts", "oop fundamentals",
    "object oriented", "object-oriented programming",
    "classes and objects", "classes and oop",
    "classes", "objects",
    "inheritance", "polymorphism",
    "inheritance and polymorphism",
    "inheritance mixins interfaces",
    "inheritance and interfaces",
    "encapsulation", "abstraction",
    "interfaces", "abstract classes",
    "interfaces and abstract classes",
    "protocols",
    "mixins", "traits",
    "modules and mixins",

    # ── Error Handling / Exceptions ──────────────────────────
    "error handling", "exception handling",
    "exceptions", "error handling and exceptions",
    "try catch", "try except",

    # ── File Handling / IO ───────────────────────────────────
    "file handling", "file io",
    "file io and streams", "file io and json",
    "streams", "file operations",

    # ── Pointers / Memory ────────────────────────────────────
    "pointers", "pointers and references",
    "references", "memory management",
    "dynamic memory allocation",
    "ownership and borrowing",
    "memory management arc",

    # ── Async / Concurrency ──────────────────────────────────
    "async", "async await", "async await concurrency",
    "async await streams", "async await coroutines",
    "async rust", "async programming",
    "asynchronous programming futures",
    "asynchronous javascript",
    "concurrency", "concurrency and parallelism",
    "concurrency goroutines channels",
    "concurrency threads",
    "coroutines", "coroutines basics",
    "coroutines structured concurrency",
    "multithreading", "multithreading concurrency",
    "select context sync package",
    "isolates concurrency",
    "goroutines", "threads",
    "futures", "promises",
    "async await promises",

    # ── Generics / Templates ─────────────────────────────────
    "generics", "templates",
    "generics traits lifetimes",
    "generics lambda streams",
    "lifetimes",

    # ── Modules / Packages ───────────────────────────────────
    "modules", "packages",
    "modules and packages", "modules crates packages",
    "modules and namespaces", "namespaces",
    "libraries packages pub",
    "gems and bundler",
    "composer and psr standards",
    "virtual environments and packaging",

    # ── Structs / Enums ──────────────────────────────────────
    "structs", "structs and enums",
    "structs and classes", "structures and unions",
    "enums", "enumerations",
    "data classes", "properties and fields",
    "properties and methods",

    # ── Null Safety / Optionals ──────────────────────────────
    "null safety", "optionals", "nullable types",

    # ── Extensions / Decorators ──────────────────────────────
    "extensions", "decorators",
    "decorators and context managers",
    "preprocessor directives",

    # ── Generators / Iterators ───────────────────────────────
    "generators", "iterators",
    "generators and iterators",
    "enumerables and iterators",
    "comprehensions", "comprehensions and functional tools",

    # ── Type System ──────────────────────────────────────────
    "type hints", "type hints and mypy",
    "union intersection types",
    "type guards narrowing",
    "enums and literals", "utility types",
    "advanced types", "type system",

    # ── Testing ──────────────────────────────────────────────
    "testing", "unit testing", "tdd",
    "testing and debugging",
    "testing and benchmarking",
    "test driven development",

    # ── Performance / Optimization ───────────────────────────
    "performance", "optimization",
    "performance and optimization",
    "performance tuning",
    "performance tuning and explain",
    "performance tuning and explain analyze",
    "query optimization",

    # ── Metaprogramming ──────────────────────────────────────
    "metaprogramming", "macros", "reflection",
    "dynamic programming",

    # ── Ruby-specific ────────────────────────────────────────
    "blocks procs lambdas", "blocks", "procs",

    # ── C#-specific ──────────────────────────────────────────
    "delegates events lambdas", "delegates", "events",
    "linq",

    # ── Modern Language Features ─────────────────────────────
    "modern python features 3.10+",
    "modern features", "modern javascript",
    "es6", "es6 features",

    # ── Database: Installation / Setup ───────────────────────
    "installation and tools", "setup", "installation",
    "tools", "database setup",

    # ── Database: CRUD ───────────────────────────────────────
    "crud", "crud operations",
    "data modification insert update delete",
    "data modification statements",
    "insert update delete",
    "select statement and filtering",
    "select statement filtering ordering",

    # ── Database: Joins / Relationships ──────────────────────
    "joins", "joins and relationships",
    "joins and subqueries",
    "joins lateral subqueries",
    "joins subqueries hierarchical queries",
    "relationships", "foreign keys",
    "relationships and referencing",

    # ── Database: Aggregation ────────────────────────────────
    "aggregation", "aggregation framework basics",
    "aggregation stages common patterns",
    "sorting grouping aggregation",
    "grouping", "group by",

    # ── Database: Indexes ────────────────────────────────────
    "indexes", "indexing",
    "indexes and performance",
    "constraints and indexes",
    "index optimization",

    # ── Database: Transactions ───────────────────────────────
    "transactions", "transactions and locking",
    "transactions isolation levels",
    "transactions and concurrency",
    "isolation levels", "acid",

    # ── Database: Schema / Design ────────────────────────────
    "schema design", "database design",
    "database design normalization",
    "normalization", "data modeling",
    "schema validation",
    "database and table creation",
    "database schema and table creation",
    "database objects tables sequences",
    "table creation constraints",

    # ── Database: Views / Stored Procedures ──────────────────
    "views", "materialized views",
    "stored procedures", "functions",
    "views stored procedures functions",
    "triggers", "triggers compound triggers",

    # ── Database: Window Functions / CTEs ────────────────────
    "window functions",
    "common table expressions",
    "common table expressions recursive",
    "common table expressions recursive ctes",
    "aggregation grouping window functions intro",
    "ctes", "recursive ctes",
    "advanced querying techniques",
    "set operations",

    # ── Database: JSON / Document Features ───────────────────
    "json support", "json support in mysql",
    "json support in oracle", "jsonb and document features",
    "jsonb", "documents and collections",

    # ── Database: Full Text Search ───────────────────────────
    "full text search", "full-text search",
    "full-text search atlas search", "atlas search",

    # ── Database: Replication / Backup ───────────────────────
    "replication", "backup and recovery",
    "backup restore and replication",
    "backup restore point-in-time recovery",
    "replication and replica sets",
    "replication logical physical",
    "dataguard physical logical",
    "point in time recovery",

    # ── Database: Security / Auth ────────────────────────────
    "security", "authentication",
    "authorization", "security authentication authorization",
    "user management privileges",
    "security roles row level security",
    "row level security",
    "sql injection security best practices",
    "advanced security features",

    # ── Database: Sharding / Partitioning ────────────────────
    "sharding", "partitioning",
    "partitioning declarative",

    # ── Database: Cloud / Atlas ──────────────────────────────
    "atlas and cloud mongodb",
    "cloud", "cloud database",

    # ── Database: ORM / Drivers ──────────────────────────────
    "mongodb drivers and odm",
    "odm", "orm", "databases and pdo", "pdo",
    "object relational mapping",

    # ── Oracle: PL/SQL ───────────────────────────────────────
    "plsql", "pl sql",
    "plsql basics anonymous blocks",
    "plsql procedures functions packages",
    "data dictionary and dynamic sql",
    "dynamic sql",

    # ── Oracle-specific ──────────────────────────────────────
    "multitenant architecture pdb cdb",
    "oracle apex low-code intro",
    "explain plan", "rman",

    # ── MySQL-specific ───────────────────────────────────────
    "mysql 8 features triggers events",

    # ── PostgreSQL-specific ──────────────────────────────────
    "postgis geospatial basics",
    "postgis", "geospatial",
    "extensions popular ones",

    # ── Change Streams / Realtime ────────────────────────────
    "change streams", "realtime", "real time",

    # ── GraphQL Subtopics ────────────────────────────────────
    "graphql introduction and concepts",
    "schema and type system",
    "queries and fields",
    "arguments variables aliases",
    "fragments and inline fragments",
    "mutations", "subscriptions",
    "introspection and schema discovery",
    "resolvers and data fetching",
    "apollo server graphql server",
    "apollo client graphql client",
    "error handling and custom errors",
    "authentication and authorization",
    "n + 1 problem dataloader",
    "dataloader",
    "schema design best practices",
    "federation and supergraph",
    "graphql code generation",
    "testing graphql apis",
    "performance caching batching",
    "relay modern graphql client intro",
    "graphql over http websocket",
    "graphql ecosystem tools",
]

# ── DURATIONS (learning-specific) ─────────────────────────────────────────────
DURATIONS = [
    # Standard & Plural Variations
    "1 day", "3 days", "10 days", "15 days", "20 days", "30 days",
    "1 week", "2 weeks", "3 weeks", "4 weeks", "7 weeks", "8 weeks",
    "1 month", "2 months", "3 months", "6 months", "12 months",

    # Shorthand & Alphanumeric
    "1d", "10d", "14d", "1w", "2w", "3w", "1m", "2m", "6m",
    "10days", "10day", "3week", "8week", "2mon", "3month",

    # Natural Language
    "one day", "five days", "ten days", "a week", "two weeks",
    "three weeks", "a month", "six months", "a couple of days",

    # Edge Cases
    "1.5 weeks", "2.5 months", "1/2 month", "48 hours", "72h",

    # Approximations & Ranges
    "about 10 days", "roughly 2 weeks", "2-3 weeks", "10 to 15 days",
    "nearly a month", "around 5 days", "up to 6 months",

    # Casual / abbreviated (Phase 2)
    "1wk", "2wks", "3wks", "4wks",
    "1mth", "2mths", "3mths",
    "abt 1 week", "abt 2 weeks", "abt 1 month", "abt 10 days",
    "~1 week", "~2 weeks", "~1 month",
    "couple weeks", "few weeks", "few days",
    "a wk", "2 wks", "3 wks",
]

# ── START DATES ───────────────────────────────────────────────────────────────
START_DATES = [
    # Relative Days
    "today", "tomorrow", "day after tomorrow", "yesterday",

    # Specific Days of the Week
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun",

    # Relative Weeks / Weekends
    "this weekend", "next weekend", "next Monday", "last Friday",
    "this coming Tuesday", "next week", "the following week",

    # Calendar Dates (Various Formats)
    "25th March", "March 25", "25 Mar", "03/25", "25/03/2024",
    "1st April", "April 1st", "1 Jan", "the 15th",

    # Vague / Fuzzy Time Windows
    "end of this week", "beginning of next week", "mid-week",
    "first week of next month", "end of the month", "early next year",
    "in two weeks", "in a fortnight",

    # Contextual Modifiers
    "ASAP", "immediately", "right away", "sometime next week",
    "by next Friday", "starting Monday",

    # Casual / abbreviated (Phase 2)
    "tmrw", "2day",
    "nxt monday", "nxt tuesday", "nxt wednesday", "nxt thursday",
    "nxt friday", "nxt saturday", "nxt sunday",
    "nxt mon", "nxt tue", "nxt wed", "nxt thu", "nxt fri",
    "nxt week", "nxt wk", "starting nxt wk", "starting nxt week",
    "from monday", "from tuesday", "from wednesday", "from thursday",
    "from friday", "from nxt week", "from tmrw",
    "this mon", "this fri", "this sat",
    "day aftr tmrw",
]

# ── COLLABORATORS ─────────────────────────────────────────────────────────────
# Same person list as scheduling_slots.py (shared across modules)
COLLABORATORS = [
    'Aamir', 'Abbas', 'Abdul', 'Abdul Aziz', 'Abdul Haq', 'Abdullah',
    'Abeeha', 'Abhishek', 'Abid', 'Abida', 'Abiha', 'Abrar', 'Adil',
    'Adnan', 'Afzal', 'Ahmad', 'Ahmed', 'Ahsan', 'Aisha', 'Aiza', 'Aizah',
    'Ajeet', 'Ajit', 'Akbar', 'Akhtar', 'Akif', 'Akmal', 'Akram', 'Alam',
    'Ali', 'Aliya', 'Almas', 'Amanullah', 'Amar', 'Ameer', 'Amin', 'Amina',
    'Amir', 'Amit', 'Amjad', 'Ammar', 'Amna', 'Amrita', 'Anas', 'Anil',
    'Ansar', 'Anwar', 'Aqeel', 'Aqil', 'Aqsa', 'Areej', 'Arif', 'Arshad',
    'Arun', 'Asad', 'Asadullah', 'Asees', 'Asghar', 'Ashfaq', 'Ashraf',
    'Asif', 'Asim', 'Asiya', 'Asma', 'Atif', 'Aurangzeb', 'Ayaz', 'Ayesha',
    'Aysha', 'Ayub', 'Azhar', 'Aziz', 'Azra', 'Babar', 'Baber', 'Babur',
    'Bakht', 'Bakhtiar', 'Basheer', 'Bashir', 'Benazir', 'Bilal',
    'Bismillah', 'Bushra', 'Danish', 'Daniyal', 'Daud', 'Deep', 'Deepa',
    'Deepak', 'Dilshad', 'Dinesh', 'Dip', 'Dipa', 'Dipak', 'Ehsan',
    'Esmatullah', 'Faheem', 'Fahmida', 'Faisal', 'Faiz', 'Faiza', 'Farah',
    'Fareed', 'Fareeha', 'Farhan', 'Farhana', 'Farid', 'Farida', 'Fariha',
    'Farooq', 'Farrukh', 'Farzana', 'Fateh', 'Fatima', 'Fawzia', 'Faysal',
    'Fazal', 'Feroz', 'Feroze', 'Fida', 'Firdaus', 'Firdos', 'Firdous',
    'Fouzia', 'Furqan', 'Ghulam', 'Gohar', 'Gul', 'Gulbadan', 'Gulbahar',
    'Gulnaz', 'Gulrukh', 'Gulshan', 'Gulzar', 'Habib', 'Habibullah',
    'Hafeez', 'Hafiz', 'Hafsa', 'Haider', 'Halima', 'Hameed', 'Hamid',
    'Hamidullah', 'Haneef', 'Hanif', 'Haris', 'Haroon', 'Hasan', 'Haseeb',
    'Hashim', 'Hasib', 'Hassan', 'Hayat', 'Hira', 'Humaira', 'Hussain',
    'Hyder', 'Ibrahim', 'Ihsan', 'Ikram', 'Ilyas', 'Iman', 'Imran',
    'Imtiaz', 'Imtiyaz', 'Inaaya', 'Inam', 'Inaya', 'Inayat',
    'Inayatullah', 'Iqbal', 'Iqra', 'Irfan', 'Irshad', 'Ishfaq', 'Ismail',
    'Ismat', 'Ismatullah', 'Jahangir', 'Jalal', 'Jamal', 'Jamil', 'Jamila',
    'Jamshed', 'Jannat', 'Javaid', 'Javed', 'Juma', 'Junaid', 'Kamal',
    'Kamran', 'Karan', 'Kausar', 'Khadija', 'Khaled', 'Khalid', 'Khalida',
    'Khalil', 'Khaliq', 'Khan', 'Khawaja', 'Khurram', 'Khurshid', 'Khwaja',
    'Kiran', 'Kulsoom', 'Kulsum', 'Kumar', 'Kunal', 'Laila', 'Latif',
    'Lubna', 'Luqman', 'Madan', 'Mahmood', 'Mahmud', 'Majid', 'Malala',
    'Malalai', 'Maliha', 'Malik', 'Mangal', 'Manish', 'Manohar', 'Manoj',
    'Mansoor', 'Manzoor', 'Maqsood', 'Maqsud', 'Mariyam', 'Maryam',
    'Masood', 'Masooma', 'Masuma', 'Mehmood', 'Mehmud', 'Midhat', 'Mina',
    'Mirza', 'Mohammad', 'Mohit', 'Mohsin', 'Muhammad', 'Muhammad Ali',
    'Mukhtar', 'Mumtaz', 'Munawar', 'Munawara', 'Muneer', 'Munir', 'Murad',
    'Murtaza', 'Musa', 'Muslim', 'Mustafa', 'Muzaffar', 'Nabeel', 'Nadeem',
    'Nadia', 'Nadim', 'Nadir', 'Naeem', 'Naeema', 'Naila', 'Najeeb',
    'Najiba', 'Najibullah', 'Najma', 'Nand', 'Naqibullah', 'Naresh',
    'Nargis', 'Naseem', 'Naseer', 'Nasim', 'Nasir', 'Nasreen', 'Naveed',
    'Navneet', 'Nazar', 'Nazeer', 'Nazia', 'Nazir', 'Neha', 'Nida',
    'Nimatullah', 'Nitish', 'Noor', 'Nur', 'Nusrat', 'Pankaj', 'Parvaiz',
    'Parveen', 'Parvez', 'Parvin', 'Pervez', 'Pooja', 'Pritam', 'Puja',
    'Qadir', 'Qamar', 'Qasim', 'Qurban', 'Rabia', 'Rafiq', 'Rahat',
    'Rahim', 'Rahman', 'Rahmat', 'Rahmatullah', 'Rahul', 'Raj', 'Raja',
    'Rajesh', 'Rakesh', 'Raman', 'Ramzan', 'Rana', 'Rani', 'Rasheed',
    'Rashid', 'Rashida', 'Rasool', 'Raza', 'Razia', 'Rehana', 'Rehman',
    'Rehmat', 'Ritu', 'Rizwan', 'Rizwana', 'Rubab', 'Rukhsana', 'Saadia',
    'Saba', 'Sabeeha', 'Sabeen', 'Sabiha', 'Sabir', 'Sadaf', 'Saddam',
    'Sadia', 'Sadiq', 'Saeed', 'Saeeda', 'Sagar', 'Sahib', 'Sahil', 'Saif',
    'Saifullah', 'Saima', 'Saira', 'Sajida', 'Sajjad', 'Sakina', 'Salamat',
    'Saleem', 'Salim', 'Salma', 'Salman', 'Samar', 'Sami', 'Samia',
    'Samina', 'Sana', 'Sandeep', 'Sandip', 'Sanjeev', 'Sanjiv', 'Santosh',
    'Sardar', 'Sayfullah', 'Shabana', 'Shabnam', 'Shafiq', 'Shaheen',
    'Shahid', 'Shahida', 'Shahjahan', 'Shahnaz', 'Shahrukh', 'Shahzad',
    'Shahzada', 'Shakir', 'Shama', 'Shameem', 'Shamim', 'Shams', 'Shandar',
    'Sharif', 'Shaukat', 'Shazia', 'Shehnaz', 'Shekhar', 'Sher', 'Shiv',
    'Shoaib', 'Shukria', 'Siddiq', 'Siddiqa', 'Sikandar', 'Simran',
    'Sitara', 'Sohail', 'Subhan', 'Suhail', 'Sultan', 'Sultana', 'Sumeet',
    'Sumit', 'Sunil', 'Swaran', 'Syed', 'Syeda', 'Tabassum', 'Tahir',
    'Tahira', 'Taj', 'Talat', 'Talha', 'Talib', 'Tariq', 'Tarun',
    'Tasleem', 'Taslim', 'Tasneem', 'Umair', 'Umar', 'Usman', 'Uzair',
    'Varun', 'Vijay', 'Vinod', 'Vishal', 'Waheed', 'Waheeda', 'Wahid',
    'Wahida', 'Wali', 'Waqar', 'Waqas', 'Waqqas', 'Waseem', 'Yama',
    'Yaqoob', 'Yaseen', 'Yash', 'Yasin', 'Yasir', 'Yasmeen', 'Yasmin',
    'Yogesh', 'Younus', 'Yousaf', 'Yousuf', 'Yusuf', 'Zafar', 'Zaheer',
    'Zahid', 'Zahida', 'Zahir', 'Zahra', 'Zain', 'Zainab', 'Zakia',
    'Zaman', 'Zamir', 'Zareen', 'Zarina', 'Zarmina', 'Zawar', 'Zeenat',
    'Zehra', 'Zia', 'Ziauddin', 'Zohra', 'Zorawar', 'Zubaida', 'Zubair',
    'Zuhra', 'Zulekha', 'Zulfaqar', 'Zulfikar', 'Zulfiqar',
]
