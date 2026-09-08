# TradeQuest Implementation Contract

All application endpoints use `/api`. JSON errors use `{ "detail": "message" }`.
Sessions use HttpOnly cookies. GET /api/auth/me returns {user, csrf_token}; user is null when anonymous. All POSTs require X-CSRF-Token from that response (including login/register). Frontend fetch uses credentials: include. Login/register return {user, csrf_token}; logout returns {ok:true}. User: {id,name,email,role,email_verified,onboarded,plan}; roles student and educator_admin. Development email tokens may be returned as dev_token explicitly only outside production.

## Authentication
- POST /auth/register {name,email,password,birth_date} -> {user,csrf_token,dev_token?}; minimum age 13, no public role selection.
- POST /auth/login {email,password}
- POST /auth/logout {}
- POST /auth/verify-email {token} -> {ok:true}
- POST /auth/forgot-password {email} -> {ok:true,dev_token?}
- POST /auth/reset-password {token,password} -> {ok:true}
- POST /me/onboarding {goal,experience} -> {ok:true}
- GET /me/export -> own account data
- POST /me/delete {password} -> {ok:true}

## Learning and Simulation
- GET /me/dashboard -> {xp,level,level_name,next_level_xp,streak,completed_lessons,badges:[{id,name,description}],onboarded,goal,experience}
- GET /lessons -> [{id,title,description,content,question,options:[string],xp,premium,completed,locked}]
- POST /lessons/{id}/complete {answer:integer} -> {correct,xp_awarded,message}; score server-side, XP once per lesson.
- GET /me/rewards -> {xp,level,level_name,next_level_xp,streak,badges:[{id,name,description}],ledger:[{id,amount,reason,created_at}],catalog:[{id,name,description,cost,owned}]}
- POST /me/rewards/redeem {reward_id} -> {ok:true}; cosmetic unlock costs use earned spendable credits separate from lifetime XP (return credits in rewards).
- GET /simulation -> {summary:{sim_day,sim_date,prices,last_return,resources},companies:[{ticker,name,region}],events:[{id,headline,report,category,date,region,severity}],portfolio:{cash,holdings,trades,value}}
- POST /simulation/advance {} -> {ok:true}; own world only, no XP for advancing/trading.
- POST /simulation/trade {side,ticker,qty,thesis} -> {message}; finite positive integer qty; private simulations, server ownership.
- POST /simulation/reflect {text} -> {xp_awarded,message}; meaningful reflection length and one reward per real UTC day.

## Educator
- GET /classes -> [{id,name,code,member_count}]; owned classes for educator, joined classes for student.
- POST /classes {name} -> {id,name,code}
- POST /classes/join {code} -> {ok:true}
- GET /classes/{id} -> {id,name,code,students:[{id,name,xp,completed_lessons}],assignments:[{id,title,lesson_id}]}; owner only.
- POST /classes/{id}/assignments {lesson_id,title} -> {ok:true}
- POST /classes/{id}/rewards {student_id,amount,reason,idempotency_key} -> {ok:true}; max 100 XP per student per UTC day; ownership and membership required.
- POST /classes/{id}/remove {student_id} -> {ok:true}

## Plans
- GET /plans -> {billing_enabled:false,plans:[{id,name,monthly_price,annual_price,features:[string]}]}
- GET /me/subscription -> {plan,status,mock_enabled}
- POST /me/subscription/mock {plan:free|premium} -> {ok:true}; development only, never production.

Implementation: FastAPI + SQLAlchemy; SQLite default for runnable local setup, DATABASE_URL accepts PostgreSQL. Argon2 passwords, durable sessions/reward ledger, transactions and uniqueness. New backend launched via python aether_backend.py preserving old simulation engine and existing JSON save untouched. Two accounts seeded through CLI with environment passwords only. New UI uses rounded Nunito-style fonts, navy/teal/lilac learning workbook visual language, responsive accessible navigation. No real billing or externally sent email without configuration; display development mode truthfully.
