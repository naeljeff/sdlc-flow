# UI work: design from the product and verify the surface

Use this when changing a component, layout, interaction, styling system, or motion. A single mechanical value correction can use the core loop alone.

1. Inspect the current route, component, tokens, states, and nearby UI patterns. Read project design guidance and user-provided references. Decide whether the request preserves an established visual language or asks for a new one. For an existing product, keep shared components and tokens coherent unless the user wants a redesign.
2. Define the intended user action and visible states: initial, loading, empty, error, success, focus, hover/press, and narrow/wide viewport where relevant. Keep copy and product facts grounded in the project.
3. If a new direction is needed, write a brief design intent before coding: audience, mood, hierarchy, type, color, spacing, imagery, and one distinctive detail that fits the product. Choose a coherent set rather than a collection of unrelated effects. Keep content readable and avoid decorative motion that conceals state.
4. Reuse the design system and platform conventions where present. Check contrast, keyboard access, labels, focus order, responsive layout, reduced-motion preference, and touch targets as applicable. Motion should clarify state or hierarchy.
5. Implement one coherent slice, then inspect it in the actual browser or device when available. Exercise the interaction and relevant viewport/theme variants. Record screenshot provenance and what the image showed; a screenshot without the route and state is weak evidence. Check typography, alignment, density, and visual hierarchy as well as functional behavior.
6. Fix observed defects and recheck the affected surface. If only source-level checks are available, report UI behavior as unverified rather than inferring visual quality from a build.

For deeper guidance, read the bundled [visual-direction source](../vendor/anthropic/frontend-design.md) when creating a new aesthetic and the [UI engineering source](../vendor/addy/frontend.md) for complex states. Their commands and paths are examples, not this skill's runtime requirements.
