import {
  Award, Brain, ClipboardCheck, Compass, Crown, Flame, GraduationCap, Languages, Search, Sprout, Timer, Trophy, Zap,
} from "lucide-react";

// Badge icon names sent by the API (see tatvax/gamification.py).
export const BADGE_ICONS = {
  sprout: Sprout, search: Search, "graduation-cap": GraduationCap, "clipboard-check": ClipboardCheck,
  trophy: Trophy, brain: Brain, flame: Flame, zap: Zap, languages: Languages, award: Award,
  compass: Compass, timer: Timer, crown: Crown,
};

export const RARITY_COLOR = {
  common: "var(--c-teal)",
  rare: "var(--rarity-rare)",
  epic: "var(--rarity-epic)",
  legendary: "var(--rarity-legendary)",
};

export function BadgeIcon({ name, size = 18, ...rest }) {
  const Icon = BADGE_ICONS[name] || Award;
  return <Icon size={size} strokeWidth={1.75} aria-hidden="true" {...rest} />;
}
