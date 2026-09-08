"""Server-owned lesson scoring and cosmetic catalog. Never expose answer keys."""

LESSONS = [
    dict(id="investing-basics", title="Your first investment", description="Understand ownership and risk.",
         content="A share represents partial ownership of a company. Its price can rise or fall. Invest only money you can afford to put at risk, after setting aside an emergency fund. This fictional simulator does not provide investment advice.",
         question="What does owning a share mean?", options=["A guaranteed return", "Partial ownership in a company", "A loan with no risk"], answer=1, xp=50, premium=False),
    dict(id="diversification", title="Do not put every egg in one basket", description="Explore diversification.",
         content="Diversification spreads investments across companies, sectors and asset types. It reduces concentration risk, but does not eliminate market risk or guarantee profits. Correlated assets can still fall together.",
         question="What can diversification do?", options=["Eliminate all losses", "Guarantee growth", "Reduce concentration risk"], answer=2, xp=60, premium=False),
    dict(id="risk-and-return", title="Risk and return", description="Match risk to your time horizon.",
         content="Higher potential returns usually involve greater uncertainty. Short-term needs are poorly matched to volatile assets. Consider your time horizon, emergency savings and ability to tolerate losses before investing.",
         question="Which money is least suitable for volatile investments?", options=["Next month's rent", "Long-term surplus savings", "Fictional simulator cash"], answer=0, xp=60, premium=False),
    dict(id="compound-growth", title="Growth on growth", description="Learn how compounding works.",
         content="Compounding means earning returns on earlier returns. At a hypothetical steady 5% annual return, 100 becomes 105 after one year and 110.25 after two. Real investment returns vary, and fees and losses also compound.",
         question="At a hypothetical steady 5%, what does 100 become after two years?", options=["110", "110.25", "150"], answer=1, xp=75, premium=False),
    dict(id="reading-the-market", title="Headlines are not forecasts", description="Separate evidence from speculation.",
         content="News can change expectations, costs and demand, but prices may already reflect anticipated events. Distinguish confirmed facts from rumors. Write down a thesis and what evidence would disprove it before making a trade.",
         question="What is the strongest response to an uncertain headline?", options=["Buy immediately", "Treat rumors as facts", "Check evidence and consider what is already priced in"], answer=2, xp=80, premium=True),
    dict(id="portfolio-strategy", title="A plan you can revisit", description="Build a disciplined portfolio process.",
         content="A portfolio plan specifies goals, time horizon, diversification and review rules. Rebalancing returns allocations toward targets, potentially creating fees or taxes. Evaluate the quality of your reasoning rather than judging a single lucky result.",
         question="What should a portfolio review prioritize?", options=["Whether the plan still matches goals and risk capacity", "Yesterday's biggest winner", "Trading as often as possible"], answer=0, xp=100, premium=True),
]

MARKET_COURSES = [
    dict(id="global-foundations", market="global", title="Global investing foundations",
         description="Build a portable foundation in ownership, risk, diversification, and compounding.",
         lesson_ids=["investing-basics", "diversification", "risk-and-return", "compound-growth"]),
    dict(id="us-market", market="us", title="United States market essentials",
         description="Practice evaluating market information and maintaining a disciplined portfolio process.",
         lesson_ids=["investing-basics", "reading-the-market", "portfolio-strategy"]),
    dict(id="uk-market", market="uk", title="United Kingdom market essentials",
         description="Apply risk, diversification, and evidence-based decision making to the UK market.",
         lesson_ids=["risk-and-return", "diversification", "reading-the-market"]),
    dict(id="india-market", market="india", title="India market essentials",
         description="Explore long-term growth, uncertainty, and portfolio construction in the Indian market.",
         lesson_ids=["compound-growth", "risk-and-return", "portfolio-strategy"]),
]

CATALOG = [
    dict(id="teal-notebook", name="Teal notebook", description="A cosmetic learning notebook cover.", cost=100),
    dict(id="lilac-frame", name="Lilac frame", description="A cosmetic profile frame.", cost=200),
    dict(id="gold-bookmark", name="Gold bookmark", description="A cosmetic milestone bookmark.", cost=350),
]

PLANS = dict(billing_enabled=False, plans=[
    dict(id="free", name="Free", monthly_price=0, annual_price=0, features=["Core lessons", "Personal simulation", "Classroom participation"]),
    dict(id="premium", name="Premium preview", monthly_price=6, annual_price=48, features=["All lessons", "Advanced portfolio learning", "No real billing is available"]),
])
