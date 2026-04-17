import React, { useEffect } from 'react'
import { useTheme } from '@/utils/ThemeContext' // 👈 直接用你项目的主题上下文

export const GlobalWatermark: React.FC = () => {
    // 👇 直接从主题上下文获取当前语言（和你的页面完全一致）
    const { theme } = useTheme()
    const currentLang = theme.language // 'zh' | 'en'

    // 水印文字
    const getWatermarkText = () => {
        return currentLang === 'zh' ? '免费开源项目,禁止商用,违者必究! 举报邮箱:support@pubchat.cn' : 'Free to use! No commercial! Report to: support@pubchat.cn'
    }

    // 语言变化 → 自动重绘水印
    useEffect(() => {
        const text = getWatermarkText()

        // 先移除旧水印
        const oldMark = document.getElementById('global-watermark')
        if (oldMark) oldMark.remove()

        // 创建 canvas 生成水印图
        const canvas = document.createElement('canvas')
        canvas.width = 600
        canvas.height = 300
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        ctx.rotate((-20 * Math.PI) / 180)
        ctx.font = '16px Microsoft YaHei, Arial'
        ctx.fillStyle = 'rgba(5, 5, 5, 0.1)'
        ctx.fillText(text, 50, 220)

        // 创建水印 DOM
        const watermarkEl = document.createElement('div')
        watermarkEl.id = 'global-watermark'
        watermarkEl.style.cssText = `
        left: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none;
        background-image: url(${canvas.toDataURL()});
        z-index: 9999;
        position: fixed;
        top: 0;
    `
        document.body.appendChild(watermarkEl)

        // 清理
        return () => {
            watermarkEl.remove()
        }
    }, [currentLang])

    return null
}