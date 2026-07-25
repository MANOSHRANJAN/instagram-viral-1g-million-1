# Mosseri's IG Algorithm Framework

Source: Adam Mosseri (Head of Instagram) on the Build Your Tribe podcast with Brock Johnson. All quoted material is verbatim from the transcript.

## Core distribution model

Instagram is a recommendation-driven platform where Feed and Reels are increasingly powered by recommendations rather than follower-graph distribution. Mosseri explicitly designed for "unconnected reach" (reach from non-followers) to grow the pie.

Key architectural points:

- "Recommendations was really just an... the only viable way to maintain feed as an important place." Feed sharing was decreasing, time spent was decreasing, creating a negative feedback loop, so IG leaned into recommendations to keep feed alive.
- "I made it I pushed really hard to make sure people could see the difference between their connected and unconnected reach... because they should know where it's coming from and what to optimize for."
- The algorithm changes constantly in tiny increments, not big batch updates: "Small changes go out every day... it's very rare that there's a massive change in how we do something it's much more common that we're just trying to get a little bit better one day at a time."
- Big swings in a creator's reach are usually external, not algorithmic: "If you see a huge swing in what's going on it probably isn't there was a huge change in how we rank content it's probably more there was a huge change in the world." (Examples: Mother's Day flooding feeds, school holidays, seasonality.)
- Content understanding is multi-modal but weighted: "Right now it's disproportionately looking at the caption relative to the video relative to the audio relative to the comments in that order but that's going to change."
- IG samples key frames (16, 128, "as many as 512") plus transcribed audio plus captions plus comments to understand a video.
- Mosseri's stated priorities for the platform: "valuing original content, helping smaller creators break, and also having trends just happen quickly."

## What the algorithm rewards (signals that boost reach)

Mosseri names three primary signals when asked which metrics to focus on:

- **Sends / Shares** — the top signal. "Shares yeah because I think shares at least algorithmically speaking of course they're helpful but it's a sending a post to another human."
- **Saves** — explicitly named as one of the three but treated as below shares: "Even if the algorithm was optimized for saves a share would still be the way to reach another human being."
- **Watch time (total seconds, not just %)** — "The amount of seconds that people are spending with that piece of content not necessarily watch rate... we look at both... but it what matters more is just the over amount of time watch."

Other rewarded signals / behaviors:

- DM sends to a single person are weighted roughly equally to story re-shares: "I think they're valued relatively equally... it's kind of more meaningful if you send me something you're like I think you'd be really interested in this that is a lot more meaningful than I thought everyone might want to know this thing."
- Originality — IG actively tries to "find the original content creator when we can and swap that person into that spot" over aggregators.
- Engagement that flows from creator activity (replying to comments, posting stories) helps indirectly because it pushes viewers to the profile, "but it's not [something] that we're trying to reward."
- Comment context is being incorporated into discovery: "Sometimes where the real interesting context is is not in the piece of not in the video that someone uploaded but in the context around it which is is almost always in the comments."

## What the algorithm penalizes (kills reach)

- **Borderline / aggressive content for unconnected reach.** "If you are posting something and it's getting close to one of our rules it will be less likely to be recommended." This includes borderline-nudity that doesn't violate, aggressive content that flirts with harassment, etc. Critical caveat: "We do not downrank content from people you follow because we think it might be offensive ever."
- **Aggregated / unoriginal content.** Aggregators "get disproportionate amount of value relative to what they create" and IG is actively working to demote them in favor of originators.
- **Long gaps between posts.** "I don't think there's a big difference if you take off three months or four months... once you get to about a month [you lose signal]." Coming back after a long break, "the algorithm doesn't have much data that it's been recently trained on and so it's very likely that that new post won't perform all that great." (He calls this a byproduct, not by design.)
- **Recommendation-guideline violations** (separate from community standards) cause reach throttling without a strike.
- **Spam-adjacent / repetitive content** gets filtered out of ranked surfaces.
- **Hashtags do not penalize, but they also don't help.** Banned hashtags simply "won't turn into a link"; not a strike, "I don't think it would [affect distribution]."

## What Mosseri says about hooks / first 3 seconds

Mosseri does NOT explicitly call out a "first 3 seconds" rule or use the word "hook" in this interview. The closest signal is his framing of watch time: total seconds watched matters more than % completion, and IG looks at both. By implication, content must hold attention long enough to accumulate seconds, but he gives no prescriptive advice about openers, pattern interrupts, or 3-second rules in this transcript.

This is a notable absence: Mosseri is silent on hook craft. The agent should not put words in his mouth here.

## What Mosseri says about audience consistency / niche

Mosseri does NOT preach strict niche discipline. Several relevant quotes:

- On creator consumption habits being orthogonal to creator output: "If you only post about rock climbing and you only like watching baking videos that's great like there's nothing wrong with that... we don't use your consumption patterns as a signal of how interesting your content is for the people who are interested in your content."
- He praises a creator who deliberately rotated niches monthly: "I met a creator once that unfollowed everybody and then re-followed a bunch of people every month with a different focus so you know one one month it was about climate change one month it was about you know women's education and I was like okay that's really cool."
- His advice on content strategy is goal-anchored, not niche-anchored: "Find the overlap between content that is going to help you achieve that goal and content that is going to be compelling because if it achieves that goal and it's not compelling no one's going to see it and if it's compelling and it doesn't achieve that goal why are you doing it and then the third is that it's true to you."
- On post-level consistency: "Don't overreact to any one post because something might have been weird that day look for the patterns so for these types of posts how do they do for this other type of post how do they do and then you know double down on what works and maybe rethink what doesn't."

## What Mosseri says about CTAs and engagement bait

- DM automation via approved partners IS allowed: "We have an API it's allowed... but sometimes there are some providers that are doing shady things." So the "comment X to get the link" mechanic is sanctioned when using reputable partners.
- Warning about credential phishing: "Don't ever give anybody your password if anybody's asking you for your password like that's not probably like a trusted partner... most accounts that are compromised so that are self-compromised."
- Mosseri does NOT in this interview warn against keyword-comment CTAs as engagement bait, nor does he call out engagement bait specifically as a downranking trigger. He treats DM-trigger CTAs as a legitimate, supported part of the ecosystem.
- He never claims comments are a top-three ranking signal — sends, saves, and watch time are the three he names. So "comment below!" CTAs are not directly rewarded in his stated model.

## What Mosseri says about Reels vs Stories vs Posts

- **Feed (where Reels live)** is the highest-reach surface for creators: "Feed is for average folk to share photos or videos that they're really proud of but it's it's a very small percentage of average folk who actually post a feed post in a given day um whereas for creators it's much higher."
- **Stories and DMs are friend-graph surfaces**, not discovery: "Stories and DMs are much more about where your friends are."
- **DMs have the most photo/video volume of any surface**: "There are more photos and videos not including text shared in DMs than there are in stories every day and there are way more photos and videos shared into stories than into feed every day."
- **Short video is the priority**, capped at 3 minutes in primary flows: "We are you know a place where we want you to easily explore a bunch of interests... short video is way more like close to that friend connection use case than long video because long video becomes much less participatory."
- **IG is not optimizing for time**: "I think if you look at you know Netflix from what I can tell they optimize for time YouTube time TikTok time plus some other things... we are a place to be entertained to entertain yourself to find stuff that to explore your interests but we're also a place to connect with your friends and if we just optimize for time... for every five minute video you watch that's maybe 50 things you didn't see from other people."
- **Cross-surface play is rewarded informally**: "The coolest stuff happens when people connect the dots between these things you know they tease their video that's going to come out on Sunday and their stories on Friday."

## Surprising or counter-intuitive things he said

- **Posting time / being active when you post does NOT directly help.** "Not directly indirectly it could happen... but it's not [something] we're trying to reward I don't want people to feel like they got to get on there." Mosseri himself schedules.
- **Hashtags are not a meaningful reach lever.** "It's just not an important thing for reach." He concedes he "got a lot of hate" for saying so.
- **Watch time matters more than watch rate.** Counter to common creator advice that obsesses over % completion, he says total seconds dominate.
- **A DM share to one person is roughly equal to a story re-share.** Volume of recipients is not the dominant factor; intent is.
- **There is no shadow ban in the colloquial sense.** "The word shadow is not involved because it's in the light you're telling them" — Account Status surfaces virtually everything. The only exceptions are "the darkest of dark" safety edge cases.
- **Borderline-but-allowed content is throttled in unconnected reach but NEVER for followers.** "We do not downrank content from people you follow because we think it might be offensive ever."
- **Long breaks (a month plus) wreck future post performance** by design of the signal-decay system, not policy: "It's a byproduct of how we build things and that doesn't mean I'm happy about it."
- **A creator's consumption habits do NOT signal what their content is about.** Watching baking videos while posting rock climbing is fine and not used as a ranking signal.
- **You don't need to be in one niche.** The creator who rotated topics monthly is held up as cool, not penalized.
- **Big swings in your reach are usually about the world (holidays, seasonality, news cycles), not the algorithm.**
- **The biggest creators are likely overpaid; small creators are underpaid.** Said about brand deals, not algo, but reveals platform values.

## Direct verbatim quotes worth keeping

1. "Shares yeah because I think shares at least algorithmically speaking of course they're helpful but it's a sending a post to another human."
2. "Even if the algorithm was optimized for saves a share would still be the way to reach another human being."
3. "What matters more is just the over amount of time watch... we're not trying to optimize for time this is a common misconception."
4. "Hashtags... it's just not an important thing for reach."
5. "Don't overreact to any one post because something might have been weird that day look for the patterns... double down on what works and maybe rethink what doesn't."
6. "If you see a huge swing in what's going on it probably isn't there was a huge change in how we rank content it's probably more there was a huge change in the world."
7. "Small changes go out every day... it's very rare that there's a massive change in how we do something."
8. "We do not downrank content from people you follow because we think it might be offensive ever."
9. "If you are posting something and it's getting close to one of our rules it will be less likely to be recommended."
10. "Find the overlap between content that is going to help you achieve that goal and content that is going to be compelling... and the third is that it's true to you."
11. "Right now it's disproportionately looking at the caption relative to the video relative to the audio relative to the comments in that order."
12. "We don't use your consumption patterns as a signal of how interesting your content is for the people who are interested in your content."
13. "It is in our interest to get someone's content to every person who's really interested in it and if we're failing to do so that's bad for our business."
14. "The word shadow is not involved because it's in the light you're telling them."
15. "Ideally the person who came up with the thing and made the thing gets more views than the person who found your thing."
