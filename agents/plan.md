OroTerra — Demo Summary
What it is: A premium specialty coffee marketplace (web + mobile) that cuts out intermediaries and connects buyers directly with farmers and roasters worldwide.

What We're Demoing
1. Coffee Catalog & Discovery

10-dimension filter engine — filter by origin, variety, SCA score, flavor profile, process, altitude, and more
20-field product cards with radical transparency: lot number, harvest date, SCA score, producer story, flavor notes, farm altitude, microlot size
2. Farm Story Pages

Immersive producer storytelling — the emotional core of the platform
Photos, altitude, biography, full lot history from that farm
3. Live Microlot Auctions

Real-time bidding with countdown timer and live bid history
The biggest differentiator — no other specialty coffee platform has this
4. Subscription Tiers

3 tiers: Explorador ($50/mo), Coleccionista ($120/mo), Gran Reserva ($200/mo)
Clear recurring revenue model
5. Multi-Language Support

7 languages: English, Spanish, French, Chinese, Japanese, Hindi, Russian
6. Cross-Platform

Web app (Next.js) + Mobile app (iOS & Android via React Native)
The Market
$14–21B specialty coffee market, growing ~10%/year
Primary market: North America. Fastest growth: Asia-Pacific
Revenue Streams
8–15% commission per sale/auction
Subscriptions ($50–$200/mo)
Private label brand (OroTerra Select) at ~60% gross margin
Business Benchmark
1,000 Coleccionista subscribers = $120,000/month recurring

Demo Flow (10 min)
Land on homepage → auction countdown visible
Filter catalog → Panama + Geisha + SCA 85+
Open product card → full 20-field detail
Visit Farm page → producer story
Live Auction → place a bid in real-time ← wow moment
Subscription page → 3 tiers, pricing, CTA
Producer dashboard → how a seller uploads a lot
Admin panel → GMV, active auctions, subscriber KPIs
Tech Built So Far
Turborepo monorepo (web + mobile + API)
Fastify API with JWT auth, Prisma ORM
Auction engine with bidding routes
Subscriptions, orders, favorites, regions
Next.js web app with i18n (7 languages)
React Native mobile app