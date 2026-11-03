<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { DailyPoint } from '@/stores/stats'

echarts.use([BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{ daily: DailyPoint[] }>()

const el = ref<HTMLDivElement | null>(null)
let chart: ReturnType<typeof echarts.init> | null = null
let observer: ResizeObserver | null = null

// 白色卡片是图表底色，分隔靠这个颜色做"留白"，不是描边
const SURFACE = '#ffffff'
const C_REMEMBERED = '#2a78d6'
const C_FORGOTTEN = '#eb6834'
const GRID = '#e1e0d9'
const AXIS = '#c3c2b7'
const MUTED = '#898781'
const INK = '#0b0b0b'
const INK_SECONDARY = '#52514e'

function buildOption(daily: DailyPoint[]) {
  const dates = daily.map((d) => d.date)
  const remembered = daily.map((d) => d.good)
  const forgotten = daily.map((d) => d.total - d.good)
  const labelStep = Math.max(1, Math.ceil(dates.length / 8))

  return {
    animationDuration: 400,
    grid: { top: 36, right: 4, bottom: 4, left: 4, containLabel: true },
    legend: {
      top: 0,
      right: 0,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 16,
      textStyle: { color: INK_SECONDARY, fontSize: 12 }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(11,11,11,0.04)' } },
      backgroundColor: SURFACE,
      borderColor: 'rgba(11,11,11,0.10)',
      borderWidth: 1,
      padding: [10, 12],
      textStyle: { color: INK, fontSize: 12 },
      formatter: (params: Array<{ dataIndex: number }>) => {
        const point = daily[params[0]?.dataIndex ?? 0]
        if (!point) return ''
        const rate = point.total ? Math.round((point.good / point.total) * 100) : 0
        return [
          `<div style="font-weight:600;margin-bottom:4px">${point.date}</div>`,
          `<div>复习 ${point.total} 张 · 正确率 ${rate}%</div>`
        ].join('')
      }
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: AXIS, width: 1 } },
      axisTick: { show: false },
      axisLabel: {
        color: MUTED,
        fontSize: 11,
        // 从最近的一天往回每隔几格标一个，避免最后一天被挤掉
        interval: (index: number) => (dates.length - 1 - index) % labelStep === 0,
        formatter: (value: string) => value.slice(5)
      }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: MUTED, fontSize: 11 },
      splitLine: { lineStyle: { color: GRID, width: 1, type: 'solid' } }
    },
    series: [
      {
        name: '记住',
        type: 'bar',
        stack: 'reviews',
        data: remembered,
        barMaxWidth: 24,
        itemStyle: { color: C_REMEMBERED, borderColor: SURFACE, borderWidth: 1 }
      },
      {
        name: '没记住',
        type: 'bar',
        stack: 'reviews',
        data: forgotten,
        barMaxWidth: 24,
        itemStyle: {
          color: C_FORGOTTEN,
          borderColor: SURFACE,
          borderWidth: 1,
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  }
}

function render() {
  if (!chart) return
  chart.setOption(buildOption(props.daily), true)
}

onMounted(() => {
  if (!el.value) return
  chart = echarts.init(el.value)
  render()
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(el.value)
})

watch(() => props.daily, render, { deep: true })

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="el" class="h-72 w-full" />
</template>
