import type { UserEvent } from "./types"

export type UserEventEffect = (event: UserEvent) => void

class UserEventsEffectBus {
  private effects = new Set<UserEventEffect>()

  dispatch(event: UserEvent) {
    for (const effect of this.effects) {
      try {
        effect(event)
      } catch (error) {
        console.error("User event effect failed.", error)
      }
    }
  }

  register(effect: UserEventEffect) {
    this.effects.add(effect)

    return () => {
      this.effects.delete(effect)
    }
  }
}

const userEventsEffectBus = new UserEventsEffectBus()

export const applyUserEventEffects = (event: UserEvent) => {
  userEventsEffectBus.dispatch(event)
}

export const registerUserEventEffect = (effect: UserEventEffect) =>
  userEventsEffectBus.register(effect)
