---
name: tekla-2d-preview
description: Enforces mathematically accurate, bounding-box-driven 2D WPF vector previews with dynamically anchored callouts (>= 15 px clearance) and live Tekla color reflection for Tekla Structures Open API plugins.
---

# Precision 2D Vector Preview & Callout Rules (.NET Framework 4.8)

## 1. Coordinate-System & Bounding-Box Mandate
NEVER guess static `Canvas.Left` / `Canvas.Top` coordinates detached from the rendered geometry.
1. **Model-Space Projection:** Compute all 2D preview primitives (polygons, lines, circles, arcs) in real model units (mm) directly from active ViewModel properties.
2. **Exact Bounding Box:** Compute the union `Rect` (`MinX`, `MinY`, `MaxX`, `MaxY`) of all visible 2D geometry before placing any callout.
3. **Uniform Scale-to-Fit:** Transform model coordinates into viewport `Canvas` coordinates using a single uniform scale factor so aspect ratios never distort. Reserve outer margin padding (`>= 48 px` per side) for callout boxes.

## 2. Dynamic Callout Tracking & Clearance Rule (>= 15 px/units)
- **Zero-Touch Clearance:** Every callout label, interactive `TextBox` border, and dimension text block MUST sit strictly outside the transformed geometry bounding box with a minimum clearance of **15 pixels/units** (`Clearance >= 15.0`) from the nearest geometry edge.
- **True Anchor Tracking:** Bind each callout's leader line start point `(AnchorX, AnchorY)` to the exact transformed vertex/midpoint of the feature it measures, and its end point `(LabelX, LabelY)` to the callout box edge outside the clearance zone.
- **Collision Avoidance:** When two callouts target the same side of the bounding box (e.g., two vertical dimensions on the right), stack them with deterministic vertical/horizontal offsets so callout boxes never overlap each other or cross the part silhouette.
- **Instant Local Recalculation:** Recompute geometry, bounding box, leader lines, and callout positions whenever a bound parameter changes (`UpdateSourceTrigger=PropertyChanged`). NEVER trigger Tekla 3D `Modify()` during preview updates.

## 3. Live Tekla Color Reflection
- Bind every rendered 2D part's `Fill` and/or `Stroke` to a ViewModel `Brush` mapped from its Tekla Class/Color enum integer (via the centralized `TeklaColorPalette` lookup table).
- Changing a color in the Colours Vertical Expander or the Property Search Bar MUST immediately recolor the corresponding part in the 2D preview.
- Keep neutral construction lines, centerlines, and leader lines bound to frozen `SolidColorBrush` resources (`PresentationOptions:Freeze="True"`).

## 4. WPF Rendering Discipline
- Keep `RenderOptions.EdgeMode="Aliased"`, `SnapsToDevicePixels="True"`, and `UseLayoutRounding="True"` on the preview `Canvas`.
- Freeze dynamically generated `StreamGeometry` and `SolidColorBrush` instances in C# (`.Freeze()`) before assigning them to ViewModel properties to eliminate unnecessary WPF composition overhead.