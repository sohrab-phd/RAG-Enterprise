import { ChevronDown, ChevronRight } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

type CollapsiblePanelProps = {
  readonly title: string;
  readonly defaultOpen?: boolean;
  readonly open?: boolean;
  readonly onOpenChange?: (open: boolean) => void;
  readonly children: React.ReactNode;
  readonly className?: string;
  readonly headerExtra?: React.ReactNode;
};

export function CollapsiblePanel({
  title,
  defaultOpen = true,
  open: controlledOpen,
  onOpenChange,
  children,
  className,
  headerExtra,
}: CollapsiblePanelProps): React.JSX.Element {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(defaultOpen);
  const open = controlledOpen ?? uncontrolledOpen;

  const setOpen = (next: boolean): void => {
    if (controlledOpen === undefined) {
      setUncontrolledOpen(next);
    }
    onOpenChange?.(next);
  };

  return (
    <section className={cn("border-b border-border last:border-b-0", className)}>
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-2 text-left text-sm font-medium"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? (
            <ChevronDown className="size-4 shrink-0" aria-hidden />
          ) : (
            <ChevronRight className="size-4 shrink-0" aria-hidden />
          )}
          <span className="truncate">{title}</span>
        </button>
        {headerExtra}
      </div>
      {open ? <div className="px-3 pb-3">{children}</div> : null}
    </section>
  );
}
