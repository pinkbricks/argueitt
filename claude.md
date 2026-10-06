when a task falls into one of these areas, use the library instead of writing it fron scratch, and install it if it isn't already in the project:
- Animations, transitions, gestures: Motion (import from "motion/react"; this is the current package, formerty called "framer-motion")
- Smooth, premium scroll feel: Lenis
- Scroll-triggered / timeline animation: GSAP with ScrollTrigger
- 3D scenes: React Three Fiber with Drei helpers
- Charts and data viz: Recharts (Visx or Nivo for custom work)
- Icons: Lucide
- Command palette (Cd+K): cmdk
- Toasts / notifications: Sonner
- Drag and drop: dnd-kit
- Sortable, filterable tables: TanStack Table (formerly React Table)
- Dates: date-fns
- Confetti / celebratory moments: canvas-confetti
Always use the current version of a library's syntax. If you're unsure of the current API, check the library's docs before writing rather than relying on an older version you might remember.
* Guardrails
- Don't add a library when the platform atready does the job well. A simple fade or hover is native CSS (opacity and transform), not a dependency.
- Match the tool to the size of the job. A one-off transition doesn't justify a 30-5BKB animation runtime.
- Prefer libraries that are actively maintained and widely used.
- For performance, only aninate transform, opacity, and filter. Avoid animating width, height, or margin.
- Respect prefers-reduced-motion in every animation.
Tell me which Library you're using, and why, before installing anything new.