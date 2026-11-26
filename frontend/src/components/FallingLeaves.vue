<script setup lang="ts">
const props = withDefaults(
  defineProps<{ count?: number; opacity?: number; fixed?: boolean }>(),
  {
    count: 16,
    opacity: 0.42,
    fixed: false,
  }
)

const COLORS = ['#b98a3c', '#b4442f', '#8a9a7b', '#c9a227', '#a87b52']

const leaves = Array.from({ length: props.count }, (_, i) => ({
  id: i,
  x: Math.random() * 100,
  size: 8 + Math.random() * 9,
  dur: 10 + Math.random() * 10,
  delay: -Math.random() * 18,
  sway: (Math.random() - 0.5) * 160,
  color: COLORS[i % COLORS.length],
}))
</script>

<template>
  <div class="leaves" :class="{ fixed: props.fixed }" aria-hidden="true">
    <span
      v-for="l in leaves"
      :key="l.id"
      class="leaf"
      :style="{
        left: l.x + '%',
        width: l.size + 'px',
        height: l.size * 1.55 + 'px',
        background: l.color,
        opacity: props.opacity,
        animationDuration: l.dur + 's',
        animationDelay: l.delay + 's',
        '--sway': l.sway + 'px',
      }"
    ></span>
  </div>
</template>

<style scoped>
.leaves {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}
.leaves.fixed {
  position: fixed;
  z-index: 5;
  height: 100vh;
}
.leaf {
  position: absolute;
  top: -12vh;
  border-radius: 0 100% 0 100%;
  animation-name: leaf-fall;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
  will-change: transform;
}
@keyframes leaf-fall {
  0% {
    transform: translate3d(0, -12vh, 0) rotate(0deg);
  }
  50% {
    transform: translate3d(var(--sway), 55vh, 0) rotate(200deg);
  }
  100% {
    transform: translate3d(0, 112vh, 0) rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .leaves {
    display: none;
  }
}
</style>
