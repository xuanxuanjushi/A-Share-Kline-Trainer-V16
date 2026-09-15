# 最大回撤区间无文字版 Design QA

## Evidence

- Source visual truth: `C:\Users\ADMINI~1\AppData\Local\Temp\codex-clipboard-4814d216-d6dd-49ed-a49a-a3f6c310a825.png`
- Implementation screenshot: `D:\Young study\stock-simulator-Cust\tmp\design-qa\max-drawdown-overlay-implementation.png`
- One-day narrow screenshot: `D:\Young study\stock-simulator-Cust\tmp\design-qa\max-drawdown-overlay-narrow.png`
- Full comparison: `D:\Young study\stock-simulator-Cust\tmp\design-qa\max-drawdown-comparison-full.png`
- Focused comparison: `D:\Young study\stock-simulator-Cust\tmp\design-qa\max-drawdown-comparison-narrow.png`
- Source pixels: 2004 x 1506; implementation viewport: 1900 x 1000 at 1x density.
- State: desktop dark theme, maximum-drawdown overlay active; six-day and one-day intervals captured.

## Findings

- No actionable P0, P1, or P2 differences remain.
- Fonts and typography: no text is rendered inside the highlighted drawdown interval.
- Spacing and layout: removing the labels leaves the candlesticks unobstructed; the interval width and two boundary positions are unchanged.
- Colors and tokens: the green translucent fill and green dashed boundary lines remain unchanged.
- Image quality: no new image or icon assets were introduced.
- Copy and content: `6天`, the percentage, and `最大回撤` are all absent from the chart; the right-side account value remains visible and clickable.
- Interaction: mouse click, Space, and Enter still toggle the same interval overlay.

## Full-view Comparison Evidence

- The implementation preserves all surrounding chart panes and account rows while removing only the three requested chart labels.
- The overlay remains clearly identifiable through its translucent fill and two dashed lines.

## Focused Comparison Evidence

- The focused source/implementation comparison confirms that both the upper duration and lower two-line summary are gone.
- A one-day interval also renders without any chart text.

## Comparison History

1. The source screenshot showed the duration and two-line maximum-drawdown summary as elements to remove.
2. The label drawing path and label-layout helper were removed.
3. Post-fix six-day and one-day captures contain only the translucent interval and its dashed boundaries.

## Implementation Checklist

- [x] Remove the duration label.
- [x] Remove the percentage label.
- [x] Remove the `最大回撤` chart label.
- [x] Keep the translucent interval and both dashed boundaries.
- [x] Preserve the right-side account control and toggle interaction.
- [x] Add a regression test that the overlay does not call `drawText`.

## Open Questions

- None.

final result: passed
