<script setup lang="ts">
const props = withDefaults(defineProps<{ count?: number }>(), { count: 18 })

const CYAN = '#67e8f9'
const TEAL = '#5eead4'

const parts = Array.from({ length: props.count }, (_, i) => {
  const isText = Math.random() > 0.62
  return {
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    w: isText ? 30 + Math.random() * 40 : 16 + Math.random() * 24,
    h: isText ? 10 + Math.random() * 8 : 22 + Math.random() * 26,
    dur: 28 + Math.random() * 34,
    delay: -Math.random() * 50,
    rot: (Math.random() - 0.5) * 36,
    dx: 30 + Math.random() * 110,
    dy: -20 - Math.random() * 50,
    color: Math.random() > 0.5 ? CYAN : TEAL,
    op: 0.1 + Math.random() * 0.2,
    isText,
  }
})
</script>

<template>
  <div class="particles" aria-hidden="true">
    <span
      v-for="p in parts"
      :key="p.id"
      class="part"
      :class="{ text: p.isText }"
      :style="{
        left: p.x + '%',
        top: p.y + '%',
        width: p.w + 'px',
        height: p.h + 'px',
        borderColor: p.color,
        '--op': p.op,
        '--dx': p.dx + 'px',
        '--dy': p.dy + 'px',
        '--rot': p.rot + 'deg',
        animationDuration: p.dur + 's',
        animationDelay: p.delay + 's',
      }"
    >
      <i class="line" :style="{ background: p.color }"></i>
      <i v-if="!p.isText" class="line short" :style="{ background: p.color }"></i>
    </span>
  </div>
</template>

<style scoped>
.particles {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 1;
}
.part {
  position: absolute;
  border: 1px solid;
  border-radius: 1px;
  opacity: 0;
  padding: 4px 5px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
  animation-name: part-drift;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
  will-change: transform, opacity;
  backdrop-filter: blur(0.5px);
}
.part.text {
  border: none;
  padding: 2px 0;
}
.line {
  display: block;
  height: 1px;
  width: 100%;
  opacity: 0.55;
}
.line.short {
  width: 62%;
  opacity: 0.38;
}
@keyframes part-drift {
  0% {
    transform: translate3d(0, 0, 0) rotate(var(--rot));
    opacity: 0;
  }
  12% {
    opacity: var(--op);
  }
  82% {
    opacity: var(--op);
  }
  100% {
    transform: translate3d(var(--dx), var(--dy), 0) rotate(calc(var(--rot) + 10deg));
    opacity: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .particles {
    display: none;
  }
}
</style>
