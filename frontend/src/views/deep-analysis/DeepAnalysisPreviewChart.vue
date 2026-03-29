<script setup lang="ts">
import { Chart } from '@antv/g2'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  xKey: string
  yKey: string
  kind: 'bar' | 'line'
  rows: Record<string, unknown>[]
}>()

const containerRef = ref<HTMLDivElement | null>(null)
let chart: Chart | null = null

function toNum(v: unknown): number {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string') {
    const n = parseFloat(String(v).replace(/,/g, ''))
    return Number.isFinite(n) ? n : NaN
  }
  return NaN
}

function buildData() {
  return props.rows
    .map((r) => ({
      x: String(r[props.xKey] ?? ''),
      y: toNum(r[props.yKey]),
    }))
    .filter((d) => d.x !== '' && !Number.isNaN(d.y))
}

function renderChart() {
  chart?.destroy()
  chart = null
  if (!containerRef.value) return
  const data = buildData()
  if (data.length === 0) return

  chart = new Chart({
    container: containerRef.value,
    autoFit: true,
    paddingTop: 12,
    paddingRight: 12,
    paddingBottom: 28,
    paddingLeft: 44,
  })

  if (props.kind === 'line') {
    chart.options({
      type: 'view',
      data,
      encode: { x: 'x', y: 'y' },
      scale: {
        x: { nice: true },
        y: { nice: true, min: 0 },
      },
      axis: {
        x: {
          title: props.xKey,
          labelAutoHide: true,
          labelFontSize: 11,
          labelFill: '#5d6b82',
        },
        y: {
          title: props.yKey,
          labelFontSize: 11,
          labelFill: '#5d6b82',
          grid: true,
        },
      },
      children: [
        {
          type: 'line',
          encode: { shape: 'smooth' },
          style: { stroke: '#2f6bff', lineWidth: 2 },
        },
        {
          type: 'point',
          encode: { size: 3 },
          style: { fill: '#fff', stroke: '#2f6bff', lineWidth: 2 },
        },
      ],
    })
  } else {
    chart.options({
      type: 'view',
      data,
      encode: { x: 'x', y: 'y' },
      scale: { x: { nice: true }, y: { nice: true, min: 0 } },
      axis: {
        x: { title: props.xKey, labelAutoHide: true, labelFill: '#5d6b82' },
        y: { title: props.yKey, labelFill: '#5d6b82', grid: true },
      },
      children: [
        {
          type: 'interval',
          style: { fill: '#2f6bff', radiusTopLeft: 4, radiusTopRight: 4 },
        },
      ],
    })
  }
  chart.render()
}

onMounted(() => {
  nextTick(() => renderChart())
})

watch(
  () => [props.rows, props.xKey, props.yKey, props.kind],
  () => nextTick(() => renderChart()),
  { deep: true }
)

onBeforeUnmount(() => {
  chart?.destroy()
  chart = null
})
</script>

<template>
  <div class="da-preview-chart-wrap">
    <div ref="containerRef" class="da-preview-chart-canvas" />
  </div>
</template>

<style scoped>
.da-preview-chart-wrap {
  width: 100%;
  margin-top: 8px;
}
.da-preview-chart-canvas {
  width: 100%;
  height: 240px;
}
</style>
