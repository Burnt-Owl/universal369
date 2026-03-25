# Comedy Factory: AI Prompts

## Character Generation Prompts

### Raven — Leonardo.ai / Midjourney Reference Prompt

```
Photorealistic portrait of a woman in her early 30s, white and mixed-race,
dark hair, multiple tattoos on arms and neck, sharp observant eyes,
slightly skeptical expression, wearing casual everyday clothes (hoodie or
band tee), sitting on a couch in a dimly lit living room, TV glow in background,
coffee mug nearby. Cinematic lighting, 8k, ultra-detailed skin texture,
shot on 35mm, natural ambient light. No makeup or minimal makeup.
```

### Jax — Leonardo.ai / Midjourney Reference Prompt

```
Photorealistic portrait of a man in his early-to-mid 30s, white and mixed-race,
tattoos on arms and chest visible, slightly disheveled hair, relaxed warm
expression with a hint of confusion, holding a beer can or glass, wearing
casual clothes (t-shirt, open flannel), sitting on a couch in a dimly lit
living room, TV glow in background. Cinematic lighting, 8k, ultra-detailed,
shot on 35mm, natural ambient light. Scruffy stubble.
```

### Couch/Room Scene — Background

```
Interior living room at night, modern but lived-in, couch with pillows,
coffee table with beer cans and a laptop, TV glow illuminating the room,
low warm ambient lighting, slightly cluttered but cozy, real couple's home.
Cinematic, 8k, wide shot, empty couch ready for characters to be composited in.
```

---

## Script Generation Prompt (Claude API)

**System prompt:**
```
You write short comedy scripts for a YouTube/TikTok series called "Raven & Jax."

The format is a modern couple on their couch reacting to a real global news event.
The script is 150-200 words of natural dialogue — enough for 1-2 minutes when spoken.

CHARACTER BIBLES:

RAVEN (wife):
- Conspiracy-smart, sharp, dry humor
- Connects dots, sees patterns, usually right
- Talks fast when excited about a theory
- Catchphrases: "I literally told you this would happen." / "There are no coincidences." / "Jax. JAX. Look at me."

JAX (husband):
- Lovably drunk, clueless, warm
- Processes everything 30 seconds late
- Accidentally says profound things
- Catchphrases: "Wait — who's that again?" / "Okay but is that bad?" / "That's wild. You want another beer?"

RULES:
- Start in the middle of the conversation — they're already watching the news
- No exposition — feel like you're eavesdropping on a real couple
- Raven drives the topic, Jax reacts
- End on a punchline or Jax's accidental wisdom
- Format: RAVEN: [line] / JAX: [line] / etc.
- Max 200 words
```

**User prompt template:**
```
Today's news event: [EVENT HEADLINE AND 2-3 SENTENCE SUMMARY]

Write the Raven & Jax script reacting to this event. Make it funny, natural, and punchy.
```

---

## Title / Description Generation Prompt

**System prompt:**
```
You write YouTube Shorts and TikTok titles and descriptions for a comedy series called "Raven & Jax" — a tattooed couple on their couch reacting to world events.
She's conspiracy-smart, he's lovably clueless.

Rules:
- Title: Max 60 chars, punchy, use the event + their dynamic
- Description: 2-3 sentences. Mention the event. End with a CTA.
- Hashtags: 5-8 relevant ones including #ravenjax #couplereacts #worldnews
```

**User prompt template:**
```
Today's event: [EVENT]
Script summary: [1-2 SENTENCE SUMMARY OF THE SCRIPT]

Generate: title, description, hashtags.
```

---

## ElevenLabs Voice Settings

### Raven
- **Voice style:** Confident, sharp, mid-range female voice
- **Stability:** 0.4 (some variation — she gets excited)
- **Similarity boost:** 0.85
- **Style:** 0.6
- **Speed:** 1.05x

### Jax
- **Voice style:** Warm, casual, slightly husky male voice
- **Stability:** 0.6 (consistent — he's mellow)
- **Similarity boost:** 0.85
- **Style:** 0.4
- **Speed:** 0.95x

---

*Created: 2026-03-25 | Comedy Factory v0.1*
