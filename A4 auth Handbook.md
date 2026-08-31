# A4 — Auth · Login & Protect — Complete Handbook (Hinglish)

**Assignment:** FlyRank Internship · Backend Track · Week 2 · A4
**Goal:** Supabase Auth use karke ek secure API banana — Sign Up, Log In, Log Out, aur protected routes jo sirf logged-in users ke liye khulen.

Ye handbook tumne A4 mein jo bhi kiya hai, sab kuch step-by-step, code + comments ke saath cover karta hai — revision ke liye ya kisi aur ko sikhane ke liye use kar sakte ho.

---

## 1. Big Picture — Ye Assignment Kyun Zaroori Hai

Abhi tak (A1-A3) tumhara API **bilkul khula** tha — koi bhi URL jaanne wala kuch bhi kar sakta tha. A4 mein humne seekha:

> **Backend ab pehle "pehchanega" ki request bhejne wala kaun hai, tabhi decide karega ki use kya allow karna hai.**

**Sabse important rule jo poore assignment mein follow kiya:** humne **khud kabhi password hash nahi kiya, khud koi cryptography nahi likhi.** Supabase (ek Identity Provider) ye sab sambhalta hai — accounts store karna, passwords hash karna, tokens issue karna. Hamara kaam sirf: token receive karna, verify karna, darwaza kholna ya band karna.

### Trust Triangle (Poori Assignment Ki Neev)

Teen parties: **Client**, **Hamara Server**, **Supabase**.

| Step | Kaun Karta Hai | Kya Hota Hai |
|---|---|---|
| 1. Sign up/Login | Client → Supabase | Client email+password Supabase ko bhejta hai |
| 2. Token | Supabase → Client | Supabase check karke JWT (token) deta hai |
| 3. Request | Client → Hamara Server | Client JWT ko `Authorization` header mein bhejta hai |
| 4. Verification | Hamara Server → Supabase | Server poochta hai "ye token real hai?" |

---

## 2. Stage 0 — Supabase Setup Aur Client Init

### Kya Kiya
1. supabase.com pe free account + project banaya
2. **Project Settings → API** se **Project URL** aur **anon key** copy kiya (kabhi bhi `service_role` key use nahi ki — wo saari security bypass kar deti hai)
3. **Authentication → Sign In/Providers → Email** mein "Confirm email" **off** kiya (practice ke liye — taaki naya signup turant login kar sake)
4. `.env` file banayi (git-ignored)

### `.env` File
```
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
DATABASE_URL=postgres://postgres:dev@db:5432/tasks
PORT=8000
```

### Code — Client Initialize Karna

```python
from supabase import create_client
from dotenv import load_dotenv
import os

# .env file ki values ko environment mein load karo
load_dotenv()

# .env se Supabase ki do zaroori values nikaalo
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Supabase client banao - ye poore app mein Supabase se baat karne ka gateway hai
# (bilkul waise jaise psycopg.connect() Postgres se connection banata hai)
supabase = create_client(url, key)
```

### Key Concept
`supabase` variable ab ek **connection object** hai — jaise `cursor` object Postgres queries chalane ke liye use hota tha, waise hi `supabase` object aage saari auth calls (signup, login, verify) ke liye use hoga.

### Real Bug Jo Face Kiya
```
supabase._sync.client.SupabaseException: Invalid URL
```
**Wajah:** Docker container ke andar `.env` file automatically nahi jaati — sirf local machine pe `load_dotenv()` kaam karta hai kyunki file wahin folder mein padi hai. Docker container ek **isolated box** hai.

**Fix:** `compose.yaml` mein `env_file` directive add kiya:
```yaml
services:
  api:
    env_file:
      - .env
```
Isse poori `.env` file container ke andar environment variables ke roop mein load ho gayi.

---

## 3. Stage 1 — Sign Up Aur Login Endpoints

### Concept
`TaskCreate` model jaisa hi ek naya model banaya, is baar email+password ke liye:

```python
class AuthCredentials(BaseModel):
    email: str
    password: str
```

### Signup Endpoint

```python
@app.post('/auth/signup', status_code=201)
async def sign_up(item: AuthCredentials):
    # Pehle validate karo - email ya password khaali na ho
    if not item.email.strip() or not item.password.strip():
        raise HTTPException(status_code=400, detail="Email and password required")
    
    # Supabase ka sign-up method call karo - dictionary format mein data bhejna hota hai
    response = supabase.auth.sign_up({"email": item.email, "password": item.password})
    
    # response.user Supabase ka apna khud ka object type hai, plain dict nahi
    # .model_dump() se usse ek clean, JSON-safe dictionary mein convert karte hain
    return {"user": response.user.model_dump()}
```

### Login Endpoint

```python
@app.post('/auth/login')
async def sign_in(item: AuthCredentials):
    if not item.email.strip() or not item.password.strip():
        raise HTTPException(status_code=400, detail="Email and password required")
    
    try:
        # Supabase ka sign-in method - agar credentials galat hain, ye khud exception raise karega
        response = supabase.auth.sign_in_with_password({"email": item.email, "password": item.password})
        
        # response.session ke ANDAR access_token aur refresh_token milte hain
        # (response seedha return karna galat hai - do level neeche jaake nikaalna padta hai)
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }
    except Exception as e:
        # Agar Supabase ne credentials reject kiye, yahan pakad ke apna 401 banate hain
        raise HTTPException(status_code=401, detail="Invalid login credentials")
```

### Naya Concept: `try/except` Se External Errors Handle Karna
Abhi tak humne sirf apne khud ke checks (`if not title.strip()`) se errors banaye the. Yahan pehli baar **Supabase khud** ek error throw kar sakta hai (galat password pe) — humein use `try/except` se **pakadna** (catch karna) padta hai aur apna khud ka `401` response banana padta hai.

### Test Kaise Kiya
```bash
curl -i -X POST http://127.0.0.1:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
# -> 201

curl -i -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
# -> 200, access_token + refresh_token milte hain
```

---

## 4. Stage 2 — Public Aur "Unverified" Protected Route

### Public Endpoint (Simple)
```python
@app.get('/public/info')
async def public_info():
    return { "message": "Welcome stranger! This info is public." }
```
Koi naya concept nahi — bilkul `GET /health` jaisa.

### Protected Endpoint — Naya Concept: Headers Padhna
Abhi tak humne request se sirf **body** ya **path parameters** padhe the. Ab humein request ka **`Authorization` header** padhna hai.

**Client jo bhejta hai:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

```python
from fastapi import Header

@app.get('/protected/profile')
async def get_profile(authorization: str = Header(None)):
    # Header(None) ka matlab - agar client header bheje hi nahi, to variable None ban jaayega
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Access token required")
    
    # "Bearer " prefix hata ke sirf token wala hissa nikaalo
    token = authorization.split("Bearer ", 1)[1]
    
    if not token:
        raise HTTPException(status_code=401, detail="Access token required")
    
    # Is stage mein bas itna confirm karna hai ki token mila - verify abhi nahi karna
    return {"message": "Token received (not yet verified)", "token_preview": token[:10]}
```

### Key Concept
Is stage mein **actual verification nahi** hoti — sirf ye check hota hai ki client ne **koi token bheja hai** (chahe wo asli ho ya fake). Asli verification Stage 3 mein hota hai.

### Test
```bash
curl -i http://127.0.0.1:8000/public/info        # -> 200
curl -i http://127.0.0.1:8000/protected/profile  # -> 401 (koi header nahi)
```

---

## 5. Stage 3 — The Guard: Asli Token Verification

### Naya Method: `supabase.auth.get_user(token)`
Ye ek **network call** hai — hamara server, Supabase ke server tak jaake poochta hai "kya ye token tumne issue kiya tha, aur abhi bhi valid hai?" Isiliye isko trust kiya ja sakta hai.

```python
@app.get('/protected/profile')
async def get_profile(authorization: str = Header(None)):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Access token required")
    token = authorization.split("Bearer ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Access token required")
    
    try:
        # Supabase se poocho - ye token genuinely valid hai?
        response = supabase.auth.get_user(token)
        # Agar yahan tak pahunche, matlab token valid hai
        return {
            "id": response.user.id,
            "email": response.user.email,
            "ac_created_date": response.user.created_at
        }
    except Exception as e:
        # Token expired, tampered, ya invalid - 401 bhejo
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

### Common Mistakes Jo Face Kiye
- `response.session.id` likha tha shuru mein — galat, `get_user()` ka response `.user` object deta hai, `.session` nahi (session sirf login-response mein hota hai)
- `response.session.date` — `date` naam ka attribute exist nahi karta, sahi naam hai `created_at`
- `except` block mein sirf `return {"error": ...}` likha tha — isse status code default `200` reh jaata (galat!). `raise HTTPException(401, ...)` likhna zaroori hai taaki actual `401` status bhi jaaye

### Test (Checkpoint)
```bash
# Login se asli token lo, phir:
curl -i http://127.0.0.1:8000/protected/profile \
  -H "Authorization: Bearer <ASLI_TOKEN>"
# -> 200, user details

# Token ka ek character badal ke phir try karo
curl -i http://127.0.0.1:8000/protected/profile \
  -H "Authorization: Bearer <TAMPERED_TOKEN>"
# -> 401
```

---

## 6. Stage 4 — Middleware (Reusable Guard) Aur Logout

### Problem Jo Solve Ki
Stage 3 ka verification logic sirf **ek** endpoint mein likha tha. Agar 5 protected routes hote, to har jagah copy-paste karna padta — messy aur risky (ek jagah bhool gaye to security hole ban jaata).

### Solution — FastAPI Dependency (Middleware Ka FastAPI Version)

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # HTTPBearer khud hi Authorization header padh leta hai,
    # "Bearer " prefix check karta hai, aur agar missing/malformed hai to khud 401/403 de deta hai
    token = credentials.credentials  # seedha token milta hai, manual "Bearer " nikaalne ki zaroorat nahi
    
    try:
        response = supabase.auth.get_user(token)
        return {
            "id": response.user.id,
            "email": response.user.email,
            "ac_created_date": response.user.created_at
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

### Ab Har Protected Route Sirf Ek Line Ka Rehta Hai

```python
@app.get('/protected/profile')
async def get_profile(current_user = Depends(get_current_user)):
    return current_user

# NAYA ROUTE - bina koi naya auth code likhe, sirf same guard reuse kiya
@app.get('/protected/dashboard')
async def get_dashboard(current_user = Depends(get_current_user)):
    return {"message": f"Welcome, {current_user['email']}"}
```

### Kya Ho Raha Hai Yahan (Concept)
Jab koi request `/protected/profile` pe aati hai, FastAPI **pehle** `get_current_user` function chalata hai (jaise ek guard darwaze pe check karta hai). Agar function ne `HTTPException` raise ki, request **wahin ruk jaati hai**. Agar function ne user return kiya, wahi user `current_user` parameter mein **automatically** aa jaata hai.

### Logout Endpoint

```python
@app.post('/auth/logout', status_code=204)
async def logout(current_user = Depends(get_current_user)):
    # Logout khud ek protected route hai - koi bina login kiye logout nahi kar sakta
    supabase.auth.sign_out()
    return  # 204 = khaali body
```

### Checkpoint Jo PDF Maangta Hai
`/protected/dashboard` ko bina naya auth code likhe banaya — sirf `Depends(get_current_user)` reuse kiya. Isse prove hua ki middleware **sach mein reusable hai**.

---

## 7. Stage 5 — Swagger UI Mein Lock Icon

### Concept
`HTTPBearer()` sirf token check hi nahi karta — ye Swagger UI ko bhi batata hai "is route ko bearer token chahiye," isliye Swagger khud-ba-khud padlock icon dikha deta hai.

**Jab humne Stage 4 mein `HTTPBearer()` ko `get_current_user` ke andar use kiya**, tab automatically saare protected routes (`profile`, `dashboard`, `logout`) ke aage padlock aa gaya — koi extra code nahi likhna pada.

### Kaise Test Kiya
1. `http://127.0.0.1:8000/docs` khola
2. Protected routes ke aage padlock icon dikha
3. Top-right "Authorize" button dabaya, apna `access_token` paste kiya (bina `Bearer ` prefix ke)
4. Uske baad "Try it out" se seedha browser se protected routes test kiye — curl ki zaroorat nahi padi

---

## 8. Stage 6 — Publish

### README Mein Kya Naya Add Kiya
- Setup instructions (Supabase project banana, `.env` fill karna)
- Endpoint table mein ek **"Auth Required?"** column add kiya
- Swagger screenshot (padlock icon aur Authorize dialog ke saath)
- Security Notes section — `anon` vs `service_role` key ka farak explicitly likha

### Sabse Critical Security Check
```bash
git log --all --full-history -- .env
```
Khaali result confirm karta hai `.env` kabhi commit nahi hua — Supabase keys leak hone se bache.

`.env.example` bhi committed kiya, sirf placeholder values ke saath:
```
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
DATABASE_URL=your_postgres_connection_string
PORT=8000
```

---

## 9. Optional Extras — Jo Kiye

### Extra 1: JWT Decode Karna (jwt.io)
Apna `access_token` [jwt.io](https://jwt.io) pe paste karke dekha — token ke **3 parts** dikhe:

| Part | Kya Hota Hai |
|---|---|
| **Header** | Batata hai kaunsa algorithm use hua signature banane mein (jaise `ES256`) |
| **Payload** | Actual data — user ki `id`, `email`, `exp` (expiry time), `role`, etc. |
| **Signature** | Ek cryptographic proof jo confirm karta hai token tamper nahi hua — sirf Supabase ke paas wo secret key hai jisse ye signature verify hota hai |

**Important learning:** Payload **koi bhi decode kar sakta hai** (ye encrypted nahi hai, sirf encoded hai — Base64) — isliye **kabhi bhi koi secret/password JWT ke andar mat daalna**, kyunki koi bhi usse padh sakta hai. Sirf signature verify karta hai ki data tamper nahi hua, data ko chhupata nahi.

### Extra 2: Expiry Experiment
Login karke access token liya, wait kiya (Supabase default: 1 ghanta expiry), phir expired token se `/protected/profile` call kiya — `401` mila.

**Kyun ye important hai:** ye **exact wajah** hai ki **refresh tokens** exist karte hain — access token jaan bujh kar short-lived rakha jaata hai (security ke liye — agar leak bhi ho jaaye, jaldi expire ho jaayega), aur refresh token (jo zyada der tak valid rehta hai) use hota hai naya access token lene ke liye, bina baar-baar login kiye.

### Baaki Extras (Nahi Kiye Abhi)
- **403 case** — samajh nahi aaya (naya concept hai, neeche explain kiya hai)
- **Logout test** (purana token dobara use karna)
- **Refresh flow**

---

## 10. Concept Jo Abhi Samajhna Baaki Hai: 401 vs 403

Ye A4 ka ek important concept hai jo tumne khud bola "samajh nahi aaya" — chalo yahin clear kar dete hain future reference ke liye.

| Status Code | Matlab | Kab Aata Hai |
|---|---|---|
| **401 Unauthorized** | "Mujhe pata hi nahi tum kaun ho" | Token missing hai, ya invalid/expired hai |
| **403 Forbidden** | "Mujhe pata hai tum kaun ho, lekin tumhe permission nahi hai" | Token valid hai (user logged in hai), lekin us user ko **is specific action ki permission nahi** |

**Real-life analogy:** 401 matlab tumhare paas office ka ID card hi nahi hai, guard andar nahi jaane dega. 403 matlab tumhare paas ID card hai (guard jaanta hai tum kaun ho), lekin tumhara card "CEO's Office" ke liye access nahi deta.

**Concept mein kaise implement hota (future reference ke liye):**
```python
@app.get('/admin/settings')
async def admin_only(current_user = Depends(get_current_user)):
    # current_user mil gaya matlab authentication pass ho gayi (401 nahi aayega)
    # ab check karna hai - kya ye user "admin" hai? (authorization)
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return {"message": "Welcome, admin"}
```

**Key difference words mein:** **Authentication** = "kaun ho tum" (401 iska jawab). **Authorization** = "kya tumhe ye karne ki permission hai" (403 iska jawab). Dono alag sawaal hain.

---

## 11. Glossary — Naye Terms Jo Is Assignment Mein Aaye

| Term | Matlab |
|---|---|
| **Authentication** | User kaun hai, verify karna (email+password match) |
| **Authorization** | Already-known user ko kya allow hai, verify karna |
| **Identity Provider (IdP)** | External service (Supabase) jo accounts/passwords/tokens manage karta hai |
| **JWT (JSON Web Token)** | Ek signed string jo user ki info carry karta hai — tamper-proof hai |
| **Access Token** | Short-lived JWT jo har request mein bheja jaata hai proof ke roop mein |
| **Refresh Token** | Longer-lived token, naya access token lene ke liye bina dobara login kiye |
| **Bearer Token** | Koi bhi token jo "jo bhi ise present kare" use honour kiya jaaye |
| **Authorization Header** | `Authorization: Bearer <token>` — standard tareeka token bhejne ka |
| **Middleware / Dependency** | Function jo route se pehle chalta hai, request ko block ya allow karta hai |
| **`anon` key** | Supabase ki public, safe-to-use key |
| **`service_role` key** | Supabase ki master key — sirf server-side, kabhi client mein nahi, saari security bypass karti hai |
| **401 vs 403** | 401 = "tum kaun ho pata nahi", 403 = "pata hai kaun ho, permission nahi" |

---

## 12. Quick Revision Checklist

- [ ] Trust triangle: Client → Supabase (credentials) → Client (token) → Server → Supabase (verify)
- [ ] Humne kabhi password hash nahi kiya — Supabase karta hai
- [ ] `anon` key safe hai app mein, `service_role` kabhi nahi
- [ ] `sign_up()` aur `sign_in_with_password()` dictionary format mein data lete hain
- [ ] Login ka access token `response.session.access_token` mein hota hai, signup ka user `response.user` mein
- [ ] `get_user(token)` ek **network call** hai Supabase ko — isiliye trustworthy hai
- [ ] `HTTPBearer()` khud header parse karta hai, missing/malformed token pe khud error deta hai
- [ ] `Depends(get_current_user)` = ek hi guard, jitne chaho utne routes pe reuse
- [ ] JWT payload **encrypted nahi hai** — sirf encoded hai, koi bhi padh sakta hai (isliye secrets kabhi andar mat daalna)
- [ ] Access token short-lived hota hai jaan bujh kar — isliye refresh token exist karta hai
- [ ] 401 = authentication fail, 403 = authorization fail (dono alag concept hain)
- [ ] `.env` mein Supabase keys, kabhi commit nahi — `git log --all --full-history -- .env` se confirm karo

---

## 13. Aage Kya — Stage 7 (AI Rematch)

Ab tum Stage 7 (bonus AI rematch) ke liye ready ho. Us stage mein:
1. Apna khud ka prompt likhna hai (bina is document se copy kiye) jisme specify karna hai: framework, Supabase as IdP, 5 routes, status codes (201/200/204/400/401), middleware verification, Swagger bearer setup
2. AI se same secured API banwani hai `ai-version/` folder mein
3. `git diff --no-index` se compare karna hai
4. README mein "AI vs me" section likhna hai — kam se kam 3 concrete differences, khaaskar:
   - Kya AI ne `Bearer ` prefix sahi parse kiya?
   - Kya AI ne koi security flaw introduce kiya (jaise `get_user` ka error check na karna)?
   - Tumhara prompt kya specify karna bhool gaya, AI ne khud kya decide kar liya?

Is handbook mein jo bhi tumne khud seekha hai, wahi tumhara benchmark banega judge karne ke liye ki AI ka version kitna accha hai — bilkul jaisa is poore assignment ka core lesson hai.