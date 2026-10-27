from pywinauto import Desktop


def main():
    print("=" * 70)
    print("LIVE CAPTIONS ACCESSIBILITY INSPECTOR")
    print("=" * 70)

    desktop = Desktop(backend="uia")

    try:
        window = desktop.window(
            title="Live Captions",
            class_name="LiveCaptionsDesktopWindow"
        )

        if not window.exists():
            print("Live Captions window was not found.")
            print("Make sure Live Captions is open.")
            return

        print("\nLive Captions window found!")
        print(f"Title: {window.window_text()}")
        print(f"Class: {window.class_name()}")

        print("\n" + "=" * 70)
        print("ACCESSIBILITY ELEMENTS")
        print("=" * 70)

        elements = window.descendants()

        if not elements:
            print("No child elements were exposed through UI Automation.")

        for index, element in enumerate(elements, start=1):
            try:
                info = element.element_info

                name = info.name or ""
                control_type = info.control_type or ""
                automation_id = info.automation_id or ""
                class_name = info.class_name or ""

                print(f"\nElement {index}")
                print(f"  Type:          {control_type}")
                print(f"  Name:          {name!r}")
                print(f"  Automation ID: {automation_id!r}")
                print(f"  Class:         {class_name!r}")

            except Exception as exc:
                print(f"\nElement {index}: Could not read properties: {exc}")

        print("\n" + "=" * 70)
        print(f"Inspection complete. Elements found: {len(elements)}")

    except Exception as exc:
        print(f"\nInspection failed: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()