import * as React from "react";
import { Link } from "react-router-dom";

import { navLabelForPath } from "@/lib/navigation";
import { cn } from "@/lib/utils";

export type BreadcrumbItem = {
  readonly label: string;
  readonly to?: string;
};

type BreadcrumbsProps = {
  readonly pathname: string;
  readonly items?: readonly BreadcrumbItem[];
  readonly className?: string;
};

export function Breadcrumbs({ pathname, items, className }: BreadcrumbsProps): React.JSX.Element {
  const crumbs: BreadcrumbItem[] =
    items && items.length > 0 ? [...items] : [{ label: navLabelForPath(pathname) }];

  return (
    <nav aria-label="Breadcrumb" className={cn("min-w-0", className)}>
      <ol className="flex flex-wrap items-center gap-1.5 text-sm text-muted-foreground">
        {crumbs.map((crumb, index) => {
          const isLast = index === crumbs.length - 1;
          return (
            <li key={`${crumb.label}-${index}`} className="flex items-center gap-1.5">
              {index > 0 ? (
                <span aria-hidden className="text-border">
                  /
                </span>
              ) : null}
              {crumb.to && !isLast ? (
                <Link to={crumb.to} className="truncate rounded-sm hover:text-foreground">
                  {crumb.label}
                </Link>
              ) : (
                <span
                  className={cn("truncate", isLast && "font-medium text-foreground")}
                  aria-current={isLast ? "page" : undefined}
                >
                  {crumb.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
