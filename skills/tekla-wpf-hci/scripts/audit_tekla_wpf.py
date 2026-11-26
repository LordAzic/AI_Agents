import re
import sys
from pathlib import Path

SKIP_DIRS = {"bin", "obj", ".git", ".vs", "packages", "node_modules", ".agents"}


def should_skip(path: Path) -> bool:
    return any(part.lower() in SKIP_DIRS for part in path.parts)


def audit_directory(root_path: str) -> int:
    root = Path(root_path).resolve()
    errors, warnings = [], []
    fields, dialogs = set(), set()

    for cs in sorted(root.rglob("*.cs")):
        if should_skip(cs):
            continue
        text = cs.read_text(encoding="utf-8", errors="ignore")

        if "PluginFormBase" in text:
            errors.append(
                f"{cs}: Legacy WinForms PluginFormBase detected. Migrate to PluginWindowBase."
            )

        if "MessageBox.Show" in text:
            errors.append(
                f"{cs}: Blocking modal MessageBox.Show detected. Use inline INotifyDataErrorInfo."
            )

        # Allow UI-only hover DispatcherTimer in isolated behavior files (no Modify/Apply calls)
        if ("DispatcherTimer" in text or re.search(r"\.(Throttle|Debounce|Sample)\s*\(", text)) and re.search(
            r"\b(Modify|Apply)\s*\(", text
        ):
            errors.append(
                f"{cs}: Timer/debounce combined with Modify()/Apply() detected. "
                "Isolate UI hover DispatcherTimer in a dedicated behavior .cs file with zero Tekla Modify/Apply calls."
            )

        if re.search(r"^\s*namespace\s+[\w\.]+\s*;", text, re.MULTILINE):
            warnings.append(
                f"{cs}: File-scoped namespace detected. Confirm <LangVersion> >= 10 in .csproj (net48 defaults to C# 7.3)."
            )

        # Track [StructuresField(...)] both raw literals and const references
        for m in re.finditer(r"\[StructuresField\(\s*([^,\)\]]+)\s*\)\]", text):
            token = m.group(1).strip()
            if token.startswith('"') and token.endswith('"'):
                key = token.strip('"')
                warnings.append(
                    f"{cs}: Raw string literal '{key}' in [StructuresField]. Centralize in AttributeNames const."
                )
                fields.add(key)
            else:
                fields.add(token)

        # Track [StructuresDialog(...)] both raw literals and const references
        for m in re.finditer(r"\[StructuresDialog\(\s*([^,\)\]]+)\s*,", text):
            token = m.group(1).strip()
            if token.startswith('"') and token.endswith('"'):
                key = token.strip('"')
                warnings.append(
                    f"{cs}: Raw string literal '{key}' in [StructuresDialog]. Centralize in AttributeNames const."
                )
                dialogs.add(key)
            else:
                dialogs.add(token)

    for key in sorted(fields.symmetric_difference(dialogs)):
        errors.append(
            f"Contract mismatch: Attribute '{key}' missing from either [StructuresField] or [StructuresDialog]."
        )

    for xaml in sorted(root.rglob("*.xaml")):
        if should_skip(xaml):
            continue
        text = xaml.read_text(encoding="utf-8", errors="ignore")

        if 'PresentationOptions:Freeze="True"' in text and "presentation/options" not in text:
            errors.append(
                f"{xaml}: PresentationOptions:Freeze used without xmlns:PresentationOptions declaration."
            )

        if re.search(r"<(Path|Canvas|Border|Grid|UniformGrid|TextBox|Expander)\b[^>]*PresentationOptions:Freeze", text, re.DOTALL):
            errors.append(
                f"{xaml}: PresentationOptions:Freeze placed on non-Freezable UIElement. Move Freeze to Freezable Resources (StreamGeometry/SolidColorBrush)."
            )

        # Check #2: Flag wide MinWidth locks on PluginWindowBase
        min_w = re.search(r"<tsd:PluginWindowBase\b[^>]*MinWidth=\"(\d+(?:\.\d+)?)\"", text, re.DOTALL)
        if min_w and float(min_w.group(1)) > 100.0:
            warnings.append(
                f"{xaml}: PluginWindowBase MinWidth={min_w.group(1)} blocks compact sidebar mode. Keep MinWidth <= 100."
            )

        if re.search(r"Binding[^}]*\bDelay\s*=", text):
            warnings.append(
                f"{xaml}: Binding Delay= detected. Verify it NEVER triggers automatic Tekla Modify()."
            )

        if "<Canvas" in text and 'RenderOptions.EdgeMode="Aliased"' not in text:
            warnings.append(
                f'{xaml}: <Canvas> missing RenderOptions.EdgeMode="Aliased" for crisp 2D lines.'
            )

        if "<PathGeometry" in text:
            warnings.append(
                f"{xaml}: <PathGeometry> detected. Prefer frozen <StreamGeometry> for static 2D vectors."
            )

        if "<StreamGeometry" in text and 'Freeze="True"' not in text:
            warnings.append(
                f'{xaml}: <StreamGeometry> missing PresentationOptions:Freeze="True".'
            )

        if "<UniformGrid" in text and 'UseLayoutRounding="True"' not in text:
            warnings.append(
                f'{xaml}: <UniformGrid> missing UseLayoutRounding="True".'
            )

        has_display_mode = 'TextFormattingMode="Display"' in text
        if "<TextBox" in text and not has_display_mode:
            warnings.append(
                f'{xaml}: <TextBox> present without TextOptions.TextFormattingMode="Display" in XAML file.'
            )

        for m in re.finditer(r'<[^>]*WpfFilterCheckBox[^>]*AttributeName="([^"{][^"]*)"', text):
            warnings.append(
                f"{xaml}: Raw string '{m.group(1)}' in WpfFilterCheckBox.AttributeName. Prefer {{x:Static local:AttributeNames.*}}."
            )

    for w in warnings:
        print(f"[WARN] {w}")
    for e in errors:
        print(f"[ERROR] {e}")

    print(f"\nAudit complete ({root}): {len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(audit_directory(target))