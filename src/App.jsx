import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  Compass,
  GraduationCap,
  Leaf,
  LockKeyhole,
  LogOut,
  Settings,
  ShieldCheck,
  Sparkles,
  Trophy,
  Wallet,
} from "lucide-react";
import { api } from "./api";

const money = (value) =>
  value == null
    ? "Not available"
    : Number(value).toLocaleString(undefined, {
        maximumFractionDigits: 2,
        minimumFractionDigits: 2,
      });
const go = (path) => {
  window.location.hash = path;
};
const link = (path) => `#${path}`;
const readRoute = () => {
  const fragment = window.location.hash.slice(1);
  const params = new URLSearchParams(fragment);
  const action = params.get("action");
  if (["verify-email", "reset-password"].includes(action)) {
    return `/${action}?token=${encodeURIComponent(params.get("token") || "")}`;
  }
  return fragment || "/";
};
const date = (value) =>
  value ? new Date(value).toLocaleString() : "Not available";

function useData(path, revision = 0) {
  const [state, setState] = useState({ loading: true });
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setState({ loading: true });
    api(path)
      .then((data) => {
        if (active) setState({ data });
      })
      .catch((error) => {
        if (active) setState({ error: error.message });
      });
    return () => {
      active = false;
    };
  }, [path, revision, retry]);
  return { ...state, retry: () => setRetry((n) => n + 1) };
}

function Load({ state, children }) {
  if (state.loading)
    return (
      <div className="notice" role="status">
        Opening your workbook...
      </div>
    );
  if (state.error)
    return (
      <div className="notice error" role="alert">
        <p>{state.error}</p>
        <button onClick={state.retry}>Try again</button>
      </div>
    );
  return children(state.data);
}

function Form({
  action,
  children,
  label = "Save changes",
  onSuccess,
  className = "",
  reset = false,
  disabled = false,
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const pending = useRef(false);
  return (
    <form
      className={`form ${className}`}
      onSubmit={async (event) => {
        event.preventDefault();
        if (pending.current || disabled) return;
        const form = event.currentTarget;
        pending.current = true;
        setBusy(true);
        setMessage(null);
        try {
          const result = await action(Object.fromEntries(new FormData(form)));
          setMessage({
            text: result?.message || "Changes saved.",
            error: false,
          });
          if (reset) form.reset();
          await onSuccess?.(result);
        } catch (error) {
          setMessage({ text: error.message, error: true });
        } finally {
          pending.current = false;
          setBusy(false);
        }
      }}
    >
      <fieldset disabled={busy || disabled}>
        {children}
        <button className="primary" type="submit">
          {busy ? "Please wait..." : label}
          {!busy && <ArrowRight size={17} />}
        </button>
      </fieldset>
      {message && (
        <div
          className={`notice ${message.error ? "error" : "success"}`}
          role={message.error ? "alert" : "status"}
        >
          {message.text}
        </div>
      )}
    </form>
  );
}

function Field({ label, name, type = "text", children, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children || <input name={name} type={type} required {...props} />}
    </label>
  );
}
function Select({ label, name, children, ...props }) {
  return (
    <Field label={label}>
      <select name={name} required {...props}>
        {children}
      </select>
    </Field>
  );
}
function Textarea({ label, name, ...props }) {
  return (
    <Field label={label}>
      <textarea name={name} required rows={4} {...props} />
    </Field>
  );
}
function Heading({ eyebrow, title, children }) {
  return (
    <header className="page-heading">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      {children && <p>{children}</p>}
    </header>
  );
}
function Card({ title, children, className = "" }) {
  return (
    <section className={`card ${className}`}>
      {title && <h2>{title}</h2>}
      {children}
    </section>
  );
}
function Empty({ children }) {
  return <p className="empty">{children}</p>;
}
function Stat({ label, value, icon: Icon = Sparkles }) {
  return (
    <div className="stat">
      <Icon size={21} />
      <div>
        <strong>{value ?? "Not available"}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}
function Brand() {
  return (
    <a className="brand" href="#/">
      <span className="brand-icon">
        <Leaf size={25} />
      </span>
      TradeQuest<span className="brand-dot">.</span>
    </a>
  );
}

function Landing() {
  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">Small lessons. Bigger perspective.</p>
          <h1>
            Your future starts
            <br />
            with a little <span>know-how.</span>
          </h1>
          <p className="hero-copy">
            Make sense of money, one good decision at a time. Learn the
            essentials, then put your thinking to work in a world where the
            money is make-believe.
          </p>
          <div className="actions">
            <a className="button primary" href="#/signup">
              Start learning free <ArrowRight size={19} />
            </a>
            <a className="button secondary" href="#/signin">
              Pick up where you left off
            </a>
          </div>
          <p className="fine">
            <ShieldCheck size={16} /> Ages 13+ · Educational simulation · No
            real-money trading
          </p>
        </div>
        <div className="workbook">
          <div className="workbook-header">
            <span>YOUR LEARNING WORKBOOK</span>
            <BookOpen size={23} />
          </div>
          <h2>
            A little wiser.
            <br />
            One step at a time.
          </h2>
          <ol className="sample-path">
            <li>
              <span>
                <BookOpen />
              </span>
              <div>
                <b>Understand the basics</b>
                <p>Build your money vocabulary.</p>
              </div>
            </li>
            <li>
              <span>
                <Compass />
              </span>
              <div>
                <b>Try a different world</b>
                <p>Explore the Aether fantasy market.</p>
              </div>
            </li>
            <li>
              <span>
                <Leaf />
              </span>
              <div>
                <b>Reflect. Learn. Grow.</b>
                <p>Let the lesson outlast the trade.</p>
              </div>
            </li>
          </ol>
          <div className="workbook-note">
            Practice decisions, not predictions.
          </div>
        </div>
      </section>
      <section className="intro-grid">
        <Card title="A path, not a pile of lessons">
          <BookOpen className="feature-icon" />
          <p>
            Short lessons and knowledge checks turn unfamiliar ideas into
            something you can use.
          </p>
        </Card>
        <Card title="A safe place to experiment">
          <Compass className="feature-icon" />
          <p>
            Follow fictional events, write a trade thesis, and see what happens
            in your own simulation.
          </p>
        </Card>
        <Card title="Progress you can explain">
          <GraduationCap className="feature-icon" />
          <p>
            Earn XP for learning and reflection. Join a classroom and learn with
            an educator.
          </p>
        </Card>
      </section>
      <div className="landing-footer">
        <p>Financial education, without the pressure.</p>
        <a href="#/pricing">
          Explore free and premium plans <ArrowRight size={17} />
        </a>
      </div>
    </>
  );
}

function DevToken({ token, reset = false }) {
  if (!token) return null;
  return (
    <aside className="notice dev">
      <strong>Development email shortcut</strong>
      <p>
        The server returned a development token. This is not proof that an email
        was delivered. Use this link to continue locally.
      </p>
      <a
        className="button secondary"
        href={`#/${reset ? "reset-password" : "verify-email"}?token=${encodeURIComponent(token)}`}
      >
        {reset ? "Open password reset" : "Verify this email"}{" "}
        <ArrowRight size={16} />
      </a>
      <details>
        <summary>Show development token</summary>
        <code>{token}</code>
      </details>
    </aside>
  );
}

function Auth({ route, user, refresh }) {
  const [token, setToken] = useState(null);
  const [done, setDone] = useState(false);
  const queryToken =
    new URLSearchParams(route.split("?")[1]).get("token") || "";
  const kind = route.split("?")[0];
  const signup = kind === "/signup";
  const signin = kind === "/signin";
  const forgot = kind === "/forgot-password";
  const verify = kind === "/verify-email";
  const title = signup
    ? "A fresh start for your future."
    : signin
      ? "Welcome back, curious mind."
      : forgot
        ? "Let’s get you back in."
        : verify
          ? "Verify your email."
          : "Choose a new password.";
  return (
    <div className="auth-layout">
      <div className="auth-aside">
        <p className="eyebrow">YOUR NEXT CHAPTER</p>
        <h2>Learning is a good investment in yourself.</h2>
        <div className="large-mark">
          <BookOpen size={72} />
        </div>
        <p>No trading pressure. No real money at risk. Just room to learn.</p>
      </div>
      <Card className="auth-card">
        <Heading eyebrow="TradeQuest account" title={title} />
        {done ? (
          <div className="notice success" role="status">
            <strong>
              {forgot
                ? "Recovery request received."
                : verify
                  ? "Email verified."
                  : signup ? "Account created." : "Password updated."}
            </strong>
            <p>
              {forgot
                ? "If this email has an account, recovery instructions are available through the configured email service. Local development may provide a shortcut below."
                : "You can continue with your account."}
            </p>
            <a
              className="button secondary"
              href={user && (verify || signup) ? "#/dashboard" : "#/signin"}
            >
              Continue <ArrowRight size={16} />
            </a>
          </div>
        ) : (
          <Form
            label={
              signup
                ? "Create free account"
                : signin
                  ? "Sign in"
                  : forgot
                    ? "Request recovery"
                    : verify
                      ? "Verify email"
                      : "Reset password"
            }
            action={async (values) => {
              if (signup) {
                const birthday = new Date(`${values.birth_date}T00:00:00`);
                const cutoff = new Date();
                cutoff.setFullYear(cutoff.getFullYear() - 13);
                if (birthday > cutoff || !Number.isFinite(birthday.getTime()))
                  throw new Error(
                    "You must be at least 13 years old to create an account.",
                  );
              }
              const endpoint = signup
                ? "register"
                : signin
                  ? "login"
                  : forgot
                    ? "forgot-password"
                    : verify
                      ? "verify-email"
                      : "reset-password";
              const result = await api(`/auth/${endpoint}`, values);
              setToken(result.dev_token || null);
              if (signup || signin) {
                await refresh();
                if (!result.dev_token) go("/dashboard");
                else setDone(true);
              } else {
                setDone(true);
                if (verify || kind === "/reset-password") await refresh();
              }
              return {
                message: signup ? "Account created." : "Request completed.",
              };
            }}
          >
            {signup && (
              <Field
                label="Your name"
                name="name"
                autoComplete="name"
                maxLength={80}
              />
            )}
            {(signup || signin || forgot) && (
              <Field
                label="Email address"
                name="email"
                type="email"
                autoComplete="email"
              />
            )}
            {!(forgot || verify) && (
              <>
                <Field
                  label={
                    signin ? "Password" : "New password (12–128 characters)"
                  }
                  name="password"
                  type="password"
                  minLength={signin ? undefined : 12}
                  maxLength={128}
                  autoComplete={signin ? "current-password" : "new-password"}
                />
                {!signin && (
                  <p className="fine">
                    Use at least five distinct characters. A long, unique
                    passphrase works well.
                  </p>
                )}
              </>
            )}
            {signup && (
              <>
                <Field
                  label="Date of birth"
                  name="birth_date"
                  type="date"
                  max={new Date().toISOString().slice(0, 10)}
                />
                <p className="fine">
                  You must be 13 or older. Your date of birth is used to check
                  eligibility. Accounts are created as learners, not
                  administrators.
                </p>
              </>
            )}
            {!(signup || signin || forgot) && (
              <Field
                label={
                  verify ? "Email verification token" : "Password reset token"
                }
                name="token"
                defaultValue={queryToken}
                autoComplete="off"
              />
            )}
          </Form>
        )}
        {signup && done && (
          <a className="button primary" href="#/dashboard">
            Open your workbook <ArrowRight size={16} />
          </a>
        )}
        <DevToken token={token} reset={forgot} />
        <div className="auth-links">
          {signin ? (
            <>
              <a href="#/forgot-password">Forgot password?</a>
              <a href="#/signup">Create an account</a>
            </>
          ) : (
            <a href="#/signin">Back to sign in</a>
          )}
        </div>
      </Card>
    </div>
  );
}

function Goals({ data, refresh }) {
  return (
    <Form
      action={(values) => api("/me/onboarding", values)}
      onSuccess={refresh}
      label="Save my learning goals"
    >
      <Field
        label="What would you like to learn?"
        name="goal"
        defaultValue={data.goal || ""}
        placeholder="For example: understand risk before investing"
        minLength={3}
        maxLength={300}
      />
      <Select
        label="How familiar are you with investing?"
        name="experience"
        defaultValue={data.experience || "beginner"}
      >
        <option value="beginner">Just getting started</option>
        <option value="some">I know a little</option>
        <option value="experienced">I have some experience</option>
      </Select>
    </Form>
  );
}

function Dashboard({ user, refreshUser }) {
  const [revision, setRevision] = useState(0);
  const state = useData("/me/dashboard", revision);
  const lessons = useData("/lessons", revision);
  return (
    <>
      <Heading
        eyebrow="Your personal workbook"
        title={`A little progress, ${user.name.split(" ")[0]}.`}
      >
        Every new idea is a step forward. Where will you start today?
      </Heading>
      <Load state={state}>
        {(data) => (
          <>
            <div className="stats">
              <Stat label="Lifetime learning XP" value={data.xp} />
              <Stat
                label={data.level_name}
                value={`Level ${data.level}`}
                icon={Leaf}
              />
              <Stat
                label="Day learning streak"
                value={data.streak}
                icon={Trophy}
              />
            </div>
            <div className="dashboard-grid">
              <section>
                <div className="section-heading">
                  <h2>Your learning path</h2>
                  <a href="#/lessons">
                    All lessons <ArrowRight size={16} />
                  </a>
                </div>
                <Load state={lessons}>
                  {(items) => <LessonPath lessons={items} />}
                </Load>
              </section>
              <aside className="stack">
                <Card
                  title={
                    data.onboarded
                      ? "Your learning intention"
                      : "First, make this yours"
                  }
                  className="lilac"
                >
                  {data.onboarded ? (
                    <>
                      <p>{data.goal}</p>
                      <a className="button secondary" href="#/settings">
                        Update your goals
                      </a>
                    </>
                  ) : (
                    <>
                      <p>A small goal gives every lesson a direction.</p>
                      <Goals
                        data={data}
                        refresh={async () => {
                          setRevision((n) => n + 1);
                          await refreshUser();
                        }}
                      />
                    </>
                  )}
                </Card>
                <Card className="navy" title="A world to learn in">
                  <Compass size={33} />
                  <p>
                    The Aether Exchange is your private fantasy market. Test an
                    idea, not your savings.
                  </p>
                  <a className="button light" href="#/simulation">
                    Enter the simulator <ArrowRight size={17} />
                  </a>
                </Card>
                <Card title="Next milestone">
                  <p>
                    {data.xp} / {data.next_level_xp} XP
                  </p>
                  <progress
                    aria-label="Progress toward next level"
                    value={data.xp}
                    max={data.next_level_xp || 1}
                  />
                  <p className="fine">
                    XP comes from learning, not trading performance.
                  </p>
                </Card>
              </aside>
            </div>
          </>
        )}
      </Load>
    </>
  );
}

function LessonPath({ lessons }) {
  if (!lessons.length)
    return (
      <Empty>
        No lessons are available yet. Check back when your course is ready.
      </Empty>
    );
  return (
    <ol className="lesson-path">
      {lessons.map((lesson, i) => (
        <li
          key={lesson.id}
          className={
            lesson.completed ? "completed" : lesson.locked ? "locked" : ""
          }
        >
          <div className="path-node">
            {lesson.completed ? (
              <Check />
            ) : lesson.locked ? (
              <LockKeyhole size={20} />
            ) : (
              String(i + 1).padStart(2, "0")
            )}
          </div>
          <div className="path-card">
            <div className="row">
              <span className="eyebrow">
                {lesson.completed
                  ? "Completed"
                  : lesson.premium
                    ? "Premium lesson"
                    : "Build your foundation"}
              </span>
              <span className="pill">{lesson.xp} XP</span>
            </div>
            <h3>{lesson.title}</h3>
            <p>{lesson.description}</p>
            <a
              className="text-action"
              href={link(lesson.locked ? "/pricing" : `/lessons/${lesson.id}`)}
            >
              {lesson.locked
                ? "Explore premium"
                : lesson.completed
                  ? "Revisit lesson"
                  : "Open lesson"}{" "}
              <ArrowRight size={17} />
            </a>
          </div>
        </li>
      ))}
    </ol>
  );
}

function Lessons({ id }) {
  const [revision, setRevision] = useState(0);
  const state = useData("/lessons", revision);
  const [result, setResult] = useState(null);
  return (
    <>
      <Heading
        eyebrow="Learn by understanding"
        title={id ? "One idea worth knowing." : "Your learning path."}
      >
        Read, think, and check your understanding. Progress is scored by the
        server.
      </Heading>
      <Load state={state}>
        {(lessons) => {
          if (!id)
            return (
              <div className="reading-width">
                <LessonPath lessons={lessons} />
              </div>
            );
          const lesson = lessons.find((item) => String(item.id) === id);
          if (!lesson)
            return (
              <Empty>
                This lesson was not found.{" "}
                <a href="#/lessons">Return to your learning path.</a>
              </Empty>
            );
          if (lesson.locked)
            return (
              <Card title={lesson.title}>
                <p>This lesson requires premium access.</p>
                <a className="button primary" href="#/pricing">
                  View plans
                </a>
              </Card>
            );
          return (
            <article className="reading-width">
              <a className="back-link" href="#/lessons">
                Back to learning path
              </a>
              <Card>
                <span className="pill">
                  {lesson.completed ? "Completed" : `${lesson.xp} learning XP`}
                </span>
                <h2>{lesson.title}</h2>
                <div className="lesson-content">{lesson.content}</div>
              </Card>
              <Card title="Put the idea to work">
                <Form
                  label="Check my answer"
                  action={(values) =>
                    api(`/lessons/${lesson.id}/complete`, {
                      answer: Number(values.answer),
                    })
                  }
                  onSuccess={(response) => {
                    setResult(response);
                    if (response.correct) setRevision((n) => n + 1);
                  }}
                >
                  <fieldset className="quiz">
                    <legend>{lesson.question}</legend>
                    {lesson.options.map((option, i) => (
                      <label className="quiz-option" key={i}>
                        <input type="radio" name="answer" value={i} required />
                        <span>{option}</span>
                      </label>
                    ))}
                  </fieldset>
                </Form>
                {result && (
                  <div
                    className={`notice ${result.correct ? "success" : ""}`}
                    role="status"
                  >
                    <strong>
                      {result.correct ? "You’ve got it." : "Keep thinking."}
                    </strong>
                    <p>{result.message}</p>
                    <p>
                      {result.xp_awarded} XP awarded. Repeat completions do not
                      earn extra XP.
                    </p>
                  </div>
                )}
              </Card>
            </article>
          );
        }}
      </Load>
    </>
  );
}

function Rewards() {
  const [revision, setRevision] = useState(0);
  const state = useData("/me/rewards", revision);
  return (
    <>
      <Heading
        eyebrow="Good habits, recognized"
        title="Look how far you’re growing."
      >
        Lifetime XP marks your progress. Spendable credits unlock cosmetics,
        never investment returns.
      </Heading>
      <Load state={state}>
        {(data) => (
          <>
            <div className="stats">
              <Stat label="Lifetime XP" value={data.xp} />
              <Stat
                label="Spendable credits"
                value={data.credits}
                icon={Wallet}
              />
              <Stat
                label={data.level_name}
                value={`Level ${data.level}`}
                icon={Leaf}
              />
            </div>
            <Card title="Your badges">
              {data.badges.length ? (
                <div className="tiles">
                  {data.badges.map((badge) => (
                    <div className="badge-card" key={badge.id}>
                      <Trophy />
                      <h3>{badge.name}</h3>
                      <p>{badge.description}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty>
                  Your first badge is ahead. Complete a lesson to begin building
                  your progress.
                </Empty>
              )}
            </Card>
            <section>
              <h2>Make your workbook yours</h2>
              <div className="tiles">
                {data.catalog.map((reward) => (
                  <Card key={reward.id} title={reward.name}>
                    <Sparkles className="feature-icon" />
                    <p>{reward.description}</p>
                    <p>
                      <b>{reward.cost} credits</b> · Cosmetic only
                    </p>
                    {reward.owned ? (
                      <span className="pill">
                        <Check size={15} /> Owned
                      </span>
                    ) : (
                      <Form
                        disabled={data.credits < reward.cost}
                        label={
                          data.credits < reward.cost
                            ? "More credits needed"
                            : "Redeem cosmetic"
                        }
                        action={() =>
                          api("/me/rewards/redeem", { reward_id: reward.id })
                        }
                        onSuccess={() => setRevision((n) => n + 1)}
                      >
                        <p className="fine">Redeeming uses credits, not lifetime XP.</p>
                        {data.credits < reward.cost && (
                          <p className="fine">
                            Keep learning to earn the remaining credits. The
                            server verifies your balance.
                          </p>
                        )}
                      </Form>
                    )}
                  </Card>
                ))}
              </div>
            </section>
            <Card title="Your reward ledger">
              <DataTable
                headers={["When", "Reason", "Amount"]}
                rows={data.ledger.map((item) => [
                  date(item.created_at),
                  item.reason,
                  `${item.amount > 0 ? "+" : ""}${item.amount}`,
                ])}
                empty="No reward activity yet. Your earned rewards will appear here."
              />
            </Card>
          </>
        )}
      </Load>
    </>
  );
}

function DataTable({ headers, rows, empty }) {
  if (!rows.length) return <Empty>{empty}</Empty>;
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label={headers.join(", ")}
    >
      <table>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header} scope="col">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((cells, i) => (
            <tr key={i}>
              {cells.map((cell, j) => (
                <td key={j}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Simulation() {
  const [revision, setRevision] = useState(0);
  const [ticker, setTicker] = useState("");
  const [qty, setQty] = useState(1);
  const [filter, setFilter] = useState("");
  const state = useData("/simulation", revision);
  return (
    <>
      <Heading
        eyebrow="The Aether Exchange · Private practice world"
        title="Real thinking. Imaginary money."
      >
        Follow the news, write your reasoning, and learn what happens next. This
        is a simulation, not financial advice.
      </Heading>
      <Load state={state}>
        {(data) => {
          const { summary, companies, events } = data;
          const portfolio = {
            ...data.portfolio,
            trades: data.portfolio.trades.map((trade) => {
              const quantity = trade.fills.reduce(
                (total, fill) => total + fill.qty,
                0,
              );
              const value = trade.fills.reduce(
                (total, fill) => total + fill.qty * fill.price,
                0,
              );
              return {
                ...trade,
                qty: quantity,
                price: quantity ? value / quantity : null,
              };
            }),
          };
          const selected = ticker || companies[0]?.ticker || "";
          const refresh = () => setRevision((n) => n + 1);
          return (
            <>
              <div className="simulation-banner">
                <div>
                  <span className="eyebrow">YOUR WORLD CLOCK</span>
                  <h2>
                    Day {summary.sim_day}{" "}
                    <span className="muted">/ {summary.sim_date}</span>
                  </h2>
                  <p>
                    Advancing changes only your world. Trades and advances do
                    not earn XP.
                  </p>
                </div>
                <Form
                  action={() => api("/simulation/advance", {})}
                  onSuccess={refresh}
                  label="Advance one day"
                />
              </div>
              <div className="stats">
                <Stat
                  label="Available simulation cash (GC)"
                  value={money(portfolio.cash)}
                  icon={Wallet}
                />
                <Stat
                  label="Total portfolio value (GC)"
                  value={money(portfolio.value)}
                  icon={Compass}
                />
                <Stat
                  label="Companies in your world"
                  value={companies.length}
                  icon={BookOpen}
                />
              </div>
              <div className="market-grid">
                <div className="stack">
                  <Card title="Market watch">
                    <Field
                      label="Find a company or region"
                      name="search"
                      value={filter}
                      onChange={(event) => setFilter(event.target.value)}
                      required={false}
                      placeholder="Search the fantasy market"
                    />
                    <DataTable
                      headers={[
                        "Company",
                        "Price (GC)",
                        "Day change",
                        "Action",
                      ]}
                      rows={companies
                        .filter((c) =>
                          `${c.ticker} ${c.name} ${c.region}`
                            .toLowerCase()
                            .includes(filter.toLowerCase()),
                        )
                        .map((company) => [
                          <>
                            <b>{company.ticker}</b>
                            <small>
                              {company.name} · {company.region}
                            </small>
                          </>,
                          money(summary.prices[company.ticker]),
                          <span
                            className={
                              (summary.last_return[company.ticker] || 0) >= 0
                                ? "positive"
                                : "negative"
                            }
                          >
                            {summary.last_return[company.ticker] == null
                              ? "Not available"
                              : `${summary.last_return[company.ticker] >= 0 ? "+" : ""}${(summary.last_return[company.ticker] * 100).toFixed(2)}%`}
                          </span>,
                          <button
                            onClick={() => {
                              setTicker(company.ticker);
                              document
                                .getElementById("trade-panel")
                                ?.scrollIntoView({ block: "start" });
                              document
                                .getElementById("trade-ticker")
                                ?.focus({ preventScroll: true });
                            }}
                          >
                            Trade <ChevronRight size={16} />
                          </button>,
                        ])}
                      empty="No companies match your search."
                    />
                  </Card>
                  <Card title="Dispatches from your world">
                    {events.length ? (
                      events.map((event) => (
                        <details className="dispatch" key={event.id}>
                          <summary>
                            <span className="eyebrow">
                              {event.region} · {event.category} · {event.date}
                            </span>
                            <h3>{event.headline}</h3>
                          </summary>
                          <p>{event.report}</p>
                          {event.severity != null && (
                            <p className="fine">
                              Event severity: {money(event.severity)}
                            </p>
                          )}
                        </details>
                      ))
                    ) : (
                      <Empty>
                        No dispatches yet. Advance a simulation day to see how
                        your world develops.
                      </Empty>
                    )}
                  </Card>
                  <Card title="World resource indices">
                    <p className="fine">
                      Simulation indices, not real commodity prices.
                    </p>
                    <div className="resource-grid">
                      {Object.entries(summary.resources).map(
                        ([name, value]) => (
                          <div key={name}>
                            <span>{name}</span>
                            <strong>{money(value)}</strong>
                          </div>
                        ),
                      )}
                    </div>
                  </Card>
                </div>
                <aside className="stack">
                  <Card title="Write your next move" className="trade-card">
                    <div id="trade-panel" />
                    <p className="fine">
                      Orders use imaginary gold crowns (GC). Actual execution
                      may differ from this estimate.
                    </p>
                    <Form
                      action={(values) =>
                        api("/simulation/trade", {
                          ...values,
                          qty: Number(values.qty),
                        })
                      }
                      onSuccess={refresh}
                      label="Place simulation order"
                    >
                      <Select
                        label="Company"
                        name="ticker"
                        id="trade-ticker"
                        value={selected}
                        onChange={(event) => setTicker(event.target.value)}
                      >
                        {companies.map((company) => (
                          <option key={company.ticker} value={company.ticker}>
                            {company.ticker} · {company.name}
                          </option>
                        ))}
                      </Select>
                      <Select label="Order side" name="side">
                        <option value="buy">Buy shares</option>
                        <option value="sell">Sell owned shares</option>
                      </Select>
                      <Field
                        label="Number of shares"
                        name="qty"
                        type="number"
                        min="1"
                        step="1"
                        value={qty}
                        onChange={(event) => setQty(event.target.value)}
                      />
                      <Textarea
                        label="Your trading thesis"
                        name="thesis"
                        minLength={10}
                        maxLength={2000}
                        placeholder="What do you expect, why, and what could prove you wrong?"
                      />
                      <div className="estimate">
                        <span>Estimated order value</span>
                        <strong>
                          {money(Number(qty) * summary.prices[selected])} GC
                        </strong>
                      </div>
                    </Form>
                  </Card>
                  <Card title="Pause. Reflect. Learn." className="lilac">
                    <p>
                      What changed your mind? Connect a world event to your
                      decision and describe what you learned.
                    </p>
                    <Form
                      action={(values) => api("/simulation/reflect", values)}
                      label="Save my reflection"
                      reset
                    >
                      <Textarea
                        label="Today’s reflection"
                        name="text"
                        minLength={40}
                        maxLength={4000}
                      />
                      <p className="fine">
                        One meaningful reflection can earn XP per real UTC day.
                        Advancing the simulation does not reset this limit.
                      </p>
                    </Form>
                  </Card>
                </aside>
              </div>
              <Card title="Your holdings">
                <DataTable
                  headers={[
                    "Ticker",
                    "Shares",
                    "Current price (GC)",
                    "Holding value (GC)",
                  ]}
                  rows={Object.entries(portfolio.holdings)
                    .filter(([, quantity]) => quantity > 0)
                    .map(([symbol, quantity]) => [
                      symbol,
                      quantity,
                      money(summary.prices[symbol]),
                      money(quantity * summary.prices[symbol]),
                    ])}
                  empty="No shares held. Read the market and write a thesis before your first practice trade."
                />
              </Card>
              <Card title="Trade history">
                <DataTable
                  headers={[
                    "Day",
                    "Side",
                    "Company",
                    "Shares",
                    "Price (GC)",
                    "Thesis",
                  ]}
                  rows={[...portfolio.trades]
                    .reverse()
                    .map((trade) => [
                      trade.day ?? trade.sim_day,
                      trade.side,
                      trade.ticker,
                      trade.qty,
                      money(trade.price),
                      trade.thesis || "No thesis recorded",
                    ])}
                  empty="No trades yet. Your simulation orders will be recorded here."
                />
              </Card>
            </>
          );
        }}
      </Load>
    </>
  );
}

function Classes({ user, id }) {
  const educator = user.role === "educator_admin";
  const [revision, setRevision] = useState(0);
  const state = useData(
    id && educator ? `/classes/${encodeURIComponent(id)}` : "/classes",
    revision,
  );
  const refresh = () => setRevision((n) => n + 1);
  return (
    <>
      <Heading
        eyebrow={educator ? "Educator workbook" : "Learn together"}
        title={
          id && educator
            ? "Your classroom, connected."
            : "A little support goes a long way."
        }
      >
        {educator
          ? "Manage your classes, assign lessons, and recognize thoughtful learning."
          : "Join a class with the code shared by your educator."}
      </Heading>
      <Load state={state}>
        {(data) =>
          id && educator ? (
            <>
              <a className="back-link" href="#/classes">
                Back to classes
              </a>
              <Card title={data.name}>
                <p>
                  Share this class code with your students:{" "}
                  <strong className="class-code">{data.code}</strong>
                </p>
                <h3>Student roster</h3>
                <DataTable
                  headers={["Student", "XP", "Lessons completed", "Membership"]}
                  rows={data.students.map((student) => [
                    student.name,
                    student.xp,
                    student.completed_lessons,
                    <Form
                      label="Remove student"
                      action={() => {
                        if (
                          !window.confirm(
                            `Remove ${student.name} from this class?`,
                          )
                        )
                          throw new Error("Removal cancelled.");
                        return api(`/classes/${id}/remove`, {
                          student_id: student.id,
                        });
                      }}
                      onSuccess={refresh}
                    />,
                  ])}
                  empty="No students yet. Share the class code so they can join."
                />
              </Card>
              <div className="two-columns">
                <Card title="Assign a lesson">
                  <AssignmentForm id={id} refresh={refresh} />
                </Card>
                <Card title="Recognize thoughtful work">
                  <p>
                    Grant up to 100 XP per student per UTC day. Reward learning,
                    not simulated profits.
                  </p>
                  {data.students.length ? (
                    <GrantForm
                      id={id}
                      students={data.students}
                      refresh={refresh}
                    />
                  ) : (
                    <Empty>Add students before granting rewards.</Empty>
                  )}
                </Card>
              </div>
              <Card title="Class assignments">
                <DataTable
                  headers={["Assignment", "Lesson"]}
                  rows={data.assignments.map((item) => [
                    item.title,
                    <a href={link(`/lessons/${item.lesson_id}`)}>
                      Open lesson <ArrowRight size={15} />
                    </a>,
                  ])}
                  empty="No assignments yet. Choose a lesson above to get started."
                />
              </Card>
            </>
          ) : (
            <>
              <div className="two-columns">
                <Card
                  title={
                    educator ? "Create a classroom" : "Join your classroom"
                  }
                >
                  <Form
                    action={(values) =>
                      api(educator ? "/classes" : "/classes/join", values)
                    }
                    label={educator ? "Create class" : "Join class"}
                    onSuccess={refresh}
                    reset
                  >
                    <Field
                      label={educator ? "Class name" : "Class code"}
                      name={educator ? "name" : "code"}
                      maxLength={100}
                    />
                  </Form>
                </Card>
                <Card className="lilac" title="Learning stays personal">
                  <GraduationCap size={35} />
                  <p>
                    {educator
                      ? "Your roster includes learning progress. Each student’s trading world remains their own."
                      : "Your educator can see your learning progress and assign lessons. Your fantasy market is still your own private practice space."}
                  </p>
                </Card>
              </div>
              <h2>{educator ? "Your classrooms" : "Joined classrooms"}</h2>
              {data.length ? (
                <div className="tiles">
                  {data.map((item) => (
                    <Card key={item.id} title={item.name}>
                      <p>{item.member_count} members</p>
                      {educator ? (
                        <a
                          className="button secondary"
                          href={link(`/classes/${item.id}`)}
                        >
                          Manage classroom <ArrowRight size={16} />
                        </a>
                      ) : (
                        <>
                          <span className="pill">
                            <Check size={15} /> Joined
                          </span>
                          <p className="fine">
                            Ask your educator which lesson to work on next.
                          </p>
                          <a href="#/lessons">Open lessons</a>
                        </>
                      )}
                    </Card>
                  ))}
                </div>
              ) : (
                <Empty>
                  {educator
                    ? "Your first classroom starts with a name. Create one above."
                    : "You haven’t joined a class yet. Ask your educator for a code."}
                </Empty>
              )}
            </>
          )
        }
      </Load>
    </>
  );
}

function AssignmentForm({ id, refresh }) {
  const state = useData("/lessons");
  return (
    <Load state={state}>
      {(lessons) => (
        <Form
          action={(values) => api(`/classes/${id}/assignments`, values)}
          label="Assign lesson"
          onSuccess={refresh}
          reset
        >
          <Field name="title" label="Assignment title" minLength={2} maxLength={120} />
          <Select label="Lesson" name="lesson_id">
            {lessons.map((lesson) => (
              <option key={lesson.id} value={lesson.id} disabled={lesson.locked}>
                {lesson.title}
                {lesson.premium ? " (Premium)" : ""}
              </option>
            ))}
          </Select>
        </Form>
      )}
    </Load>
  );
}
function GrantForm({ id, students, refresh }) {
  const key = useRef(crypto.randomUUID());
  return (
    <Form
      action={(values) =>
        api(`/classes/${id}/rewards`, {
          ...values,
          amount: Number(values.amount),
          idempotency_key: key.current,
        })
      }
      onSuccess={async () => {
        key.current = crypto.randomUUID();
        refresh();
      }}
      label="Grant learning XP"
      reset
    >
      <Select name="student_id" label="Student">
        {students.map((student) => (
          <option key={student.id} value={student.id}>
            {student.name}
          </option>
        ))}
      </Select>
      <Field
        name="amount"
        label="XP amount (1–100)"
        type="number"
        min="1"
        max="100"
        step="1"
      />
      <Textarea
        name="reason"
        label="What learning are you recognizing?"
        minLength={5}
        maxLength={300}
      />
    </Form>
  );
}

function Pricing({ user, refreshUser }) {
  const plans = useData("/plans");
  return (
    <>
      <Heading eyebrow="Room to grow" title="Start free. Stay curious.">
        Choose the learning access that fits you. No real-money trading, on any
        plan.
      </Heading>
      <Load state={plans}>
        {(data) => (
          <>
            <div className="notice">
              <ShieldCheck size={20} />
              <span>
                {data.billing_enabled
                  ? "Plan prices are shown below. Checkout is not available in this frontend."
                  : "Real billing is not enabled. There is no payment checkout and you will not be charged here."}
              </span>
            </div>
            <div className="two-columns">
              {data.plans.map((plan) => (
                <Card
                  key={plan.id}
                  className={plan.id === "premium" ? "lilac plan" : "plan"}
                  title={plan.name}
                >
                  <div className="price">
                    ${money(plan.monthly_price)}
                    <small>/ month</small>
                  </div>
                  <p>${money(plan.annual_price)} per year</p>
                  <ul className="feature-list">
                    {plan.features.map((feature) => (
                      <li key={feature}>
                        <Check size={18} />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  {!user ? (
                    <a className="button primary" href="#/signup">
                      {plan.id === "free"
                        ? "Start learning free"
                        : "Create a free account first"}{" "}
                      <ArrowRight size={16} />
                    </a>
                  ) : (
                    <span className="pill">
                      {user.plan === plan.id
                        ? "Your current plan"
                        : "See access options below"}
                    </span>
                  )}
                </Card>
              ))}
            </div>
            {user && <Subscription refreshUser={refreshUser} />}
          </>
        )}
      </Load>
    </>
  );
}
function Subscription({ refreshUser }) {
  const [revision, setRevision] = useState(0);
  const state = useData("/me/subscription", revision);
  return (
    <Load state={state}>
      {(data) => (
        <Card title="Your plan access">
          <p>
            Plan: <b>{data.plan}</b> · Status: {data.status}
          </p>
          {data.mock_enabled ? (
            <div className="notice dev">
              <h3>Development-only plan simulator</h3>
              <p>
                This is a mock switch for testing premium access. It is not a
                purchase, payment, or paid subscription.
              </p>
              <Form
                action={(values) => api("/me/subscription/mock", values)}
                label="Apply development mock plan"
                onSuccess={async () => {
                  setRevision((n) => n + 1);
                  await refreshUser();
                }}
              >
                <Select
                  name="plan"
                  label="Mock access level"
                  defaultValue={data.plan}
                >
                  <option value="free">Free</option>
                  <option value="premium">Premium (development mock)</option>
                </Select>
              </Form>
            </div>
          ) : (
            <p>
              Development plan switching is unavailable. No payment is collected
              on this page.
            </p>
          )}
        </Card>
      )}
    </Load>
  );
}

function AccountSettings({ user, refreshUser, logout }) {
  const state = useData("/me/dashboard");
  return (
    <>
      <Heading
        eyebrow="Your account, your choices"
        title="Make yourself at home."
      >
        Manage your goals, account access, and personal data.
      </Heading>
      <div className="two-columns">
        <div className="stack">
          <Card title="Your profile">
            <dl className="profile">
              <dt>Name</dt>
              <dd>{user.name}</dd>
              <dt>Email</dt>
              <dd>{user.email}</dd>
              <dt>Email status</dt>
              <dd>
                {user.email_verified ? (
                  "Verified"
                ) : (
                  <a href="#/verify-email">
                    Not verified · Enter verification token
                  </a>
                )}
              </dd>
              <dt>Account</dt>
              <dd>{user.role === "educator_admin" ? "Educator" : "Learner"}</dd>
            </dl>
            <a className="button secondary" href="#/forgot-password">
              Request a password reset
            </a>
          </Card>
          <Card title="Your learning goals">
            <Load state={state}>
              {(data) => <Goals data={data} refresh={refreshUser} />}
            </Load>
          </Card>
        </div>
        <div className="stack">
          <Card title="Take your workbook with you">
            <p>
              Download the account data returned by the server as a JSON file.
              Store your export somewhere private.
            </p>
            <Form
              label="Export my data"
              action={async () => {
                const data = await api("/me/export");
                const url = URL.createObjectURL(
                  new Blob([JSON.stringify(data, null, 2)], {
                    type: "application/json",
                  }),
                );
                const anchor = document.createElement("a");
                anchor.href = url;
                anchor.download = "tradequest-my-data.json";
                anchor.click();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
                return { message: "Your data export has been downloaded." };
              }}
            />
          </Card>
          <Card title="End this session">
            <p>
              Sign out on this browser. Your learning progress stays with your
              account.
            </p>
            <Form label="Sign out" action={logout} />
          </Card>
          <Card title="Delete your account" className="danger-zone">
            <p>
              This permanently deletes your account and associated data. Export
              anything you want to keep first.
            </p>
            <Form
              label="Permanently delete my account"
              action={async (values) => {
                if (
                  !window.confirm(
                    "Permanently delete your account and all associated data? This cannot be undone.",
                  )
                )
                  throw new Error("Account deletion cancelled.");
                const result = await api("/me/delete", {
                  password: values.password,
                });
                await refreshUser();
                go("/");
                return result;
              }}
            >
              <Field
                name="password"
                type="password"
                label="Confirm with your current password"
                autoComplete="current-password"
              />
              <label className="checkbox">
                <input type="checkbox" required /> I understand that deletion
                cannot be undone.
              </label>
            </Form>
          </Card>
        </div>
      </div>
    </>
  );
}

const navItems = [
  ["/dashboard", "My workbook", BookOpen],
  ["/lessons", "Learning path", Leaf],
  ["/simulation", "Fantasy market", Compass],
  ["/rewards", "Rewards", Trophy],
  ["/classes", "Classrooms", GraduationCap],
  ["/pricing", "Plans", Sparkles],
  ["/settings", "Settings", Settings],
];

export default function App() {
  const [route, setRoute] = useState(readRoute);
  const [session, setSession] = useState({ loading: true });
  const main = useRef(null);
  const refreshUser = async () => {
    try {
      const result = await api("/auth/me");
      setSession({ user: result.user });
      return result.user;
    } catch (error) {
      setSession({ error: error.message });
      throw error;
    }
  };
  useEffect(() => {
    refreshUser().catch(() => {});
    const navigate = () => {
      setRoute(readRoute());
      window.scrollTo(0, 0);
      requestAnimationFrame(() => main.current?.focus());
    };
    const expire = () => setSession({ user: null });
    window.addEventListener("hashchange", navigate);
    window.addEventListener("session-expired", expire);
    return () => {
      window.removeEventListener("hashchange", navigate);
      window.removeEventListener("session-expired", expire);
    };
  }, []);
  const user = session.user;
  const path = route.split("?")[0];
  const authRoute = [
    "/signin",
    "/signup",
    "/forgot-password",
    "/reset-password",
    "/verify-email",
  ].includes(path);
  const publicRoute = path === "/" || path === "/pricing" || authRoute;
  useEffect(() => {
    document.title = `${navItems.find(([href]) => path.startsWith(href))?.[1] || "Learn money, grow confidence"} | TradeQuest`;
  }, [path]);
  const logout = async () => {
    const result = await api("/auth/logout", {});
    setSession({ user: null });
    go("/signin");
    return result;
  };
  let page;
  if (!publicRoute && session.loading)
    page = (
      <div role="status" className="notice">
        Checking your session...
      </div>
    );
  else if (!publicRoute && session.error)
    page = (
      <div className="notice error" role="alert">
        <p>{session.error}</p>
        <button onClick={() => refreshUser().catch(() => {})}>
          Retry connection
        </button>
      </div>
    );
  else if (!publicRoute && !user)
    page = (
      <div className="auth-card card">
        <Heading
          eyebrow="Your workbook is private"
          title="Sign in to keep learning."
        >
          Your session may have ended. Sign in to open this page.
        </Heading>
        <a className="button primary" href="#/signin">
          Sign in <ArrowRight size={17} />
        </a>
        <a className="button secondary" href="#/signup">
          Create an account
        </a>
      </div>
    );
  else if (path === "/") page = <Landing />;
  else if (authRoute)
    page = <Auth key={route} route={route} user={user} refresh={refreshUser} />;
  else if (path === "/dashboard")
    page = <Dashboard user={user} refreshUser={refreshUser} />;
  else if (path === "/lessons" || path.startsWith("/lessons/"))
    page = <Lessons key={path} id={path.split("/")[2]} />;
  else if (path === "/simulation") page = <Simulation />;
  else if (path === "/rewards") page = <Rewards />;
  else if (path === "/classes" || path.startsWith("/classes/"))
    page = <Classes key={path} user={user} id={path.split("/")[2]} />;
  else if (path === "/pricing")
    page = <Pricing user={user} refreshUser={refreshUser} />;
  else if (path === "/settings")
    page = (
      <AccountSettings user={user} refreshUser={refreshUser} logout={logout} />
    );
  else
    page = (
      <Card title="This page isn’t in your workbook.">
        <a href={user ? "#/dashboard" : "#/"}>Go back to the beginning</a>
      </Card>
    );
  const appShell = user && !authRoute && path !== "/";
  return (
    <div className={appShell ? "app-shell" : "public-shell"}>
      <a
        className="skip-link"
        href="#main"
        onClick={(event) => {
          event.preventDefault();
          main.current?.focus();
        }}
      >
        Skip to content
      </a>
      {appShell ? (
        <aside className="sidebar">
          <Brand />
          <div className="sidebar-label">A LITTLE WISER, EVERY DAY</div>
          <nav aria-label="Main navigation">
            {navItems.map(([href, label, Icon]) => (
              <a
                href={link(href)}
                key={href}
                className={path.startsWith(href) ? "active" : ""}
                aria-current={path.startsWith(href) ? "page" : undefined}
              >
                <Icon size={21} />
                <span>{label}</span>
                {path.startsWith(href) && <ChevronRight size={16} />}
              </a>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <span className="avatar">
              {user.name.slice(0, 1).toUpperCase()}
            </span>
            <div>
              <b>{user.name}</b>
              <small>
                {user.role === "educator_admin"
                  ? "Educator account"
                  : "Your learning journey"}
              </small>
            </div>
            <a href="#/settings" aria-label="Account settings">
              <Settings size={20} />
            </a>
          </div>
        </aside>
      ) : (
        <header className="public-header">
          <Brand />
          <nav aria-label="Main navigation">
            <a href="#/pricing">Plans</a>
            <a href={user ? "#/dashboard" : "#/signin"}>
              {user ? "My workbook" : "Sign in"}
            </a>
            <a
              className="button primary"
              href={user ? "#/simulation" : "#/signup"}
            >
              {user ? "Practice" : "Start free"} <ArrowRight size={16} />
            </a>
          </nav>
        </header>
      )}
      <div className="main-wrap">
        {appShell && (
          <div className="topbar">
            <span>
              <BookOpen size={17} /> Your money-learning companion
            </span>
            <span className="pill">
              {user.plan === "premium" ? "Premium access" : "Free learner"}
            </span>
          </div>
        )}
        <main id="main" ref={main} tabIndex={-1}>
          {user && !user.email_verified && !authRoute && (
            <div className="verify-banner">
              <ShieldCheck size={19} />
              <span>Your email isn’t verified yet.</span>
              <a href="#/verify-email">
                Enter verification token <ArrowRight size={15} />
              </a>
            </div>
          )}
          {page}
        </main>
        <footer className="site-footer">
          <Brand />
          <p>A little learning goes a long way.</p>
          <span>Education only. Fictional markets. No financial advice.</span>
        </footer>
      </div>
    </div>
  );
}
