import React, { useMemo } from 'react';
import { LayoutGrid } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { cn } from '../../lib/utils';

type ItemId = string | number;

interface MultiDisplayViewProps<T extends { id: ItemId }> {
  items: T[];
  selectedItems: T[];
  loading?: boolean;
  maxSelected: number;
  columns: number;
  getLabel: (item: T) => string;
  onToggle: (item: T) => void;
  renderItem: (item: T) => React.ReactNode;
}

const gridColumnClasses: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 xl:grid-cols-2',
  3: 'grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3',
  4: 'grid-cols-1 md:grid-cols-2 2xl:grid-cols-4',
};

export function MultiDisplayView<T extends { id: ItemId }>({
  items,
  selectedItems,
  loading = false,
  maxSelected,
  columns,
  getLabel,
  onToggle,
  renderItem,
}: MultiDisplayViewProps<T>) {
  const { t } = useTranslation();
  const selectedIds = useMemo(
    () => new Set(selectedItems.map((item) => String(item.id))),
    [selectedItems],
  );
  const selectionFull = selectedItems.length >= maxSelected;

  return (
    <div
      className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border bg-card lg:flex-row"
      data-page-region="multi-display"
    >
      <aside className="flex max-h-64 shrink-0 flex-col border-b bg-muted/10 lg:max-h-none lg:w-72 lg:border-b-0 lg:border-r">
        <div className="space-y-2 border-b p-3">
          <p className="text-xs text-muted-foreground">
            {t('multi_display.selection_count', 'Selected {{count}} / {{max}}', {
              count: selectedItems.length,
              max: maxSelected,
            })}
          </p>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          {loading && items.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              {t('common.loading', 'Loading...')}
            </div>
          ) : items.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              {t('common.no_result', 'No results')}
            </div>
          ) : (
            items.map((item) => {
              const checked = selectedIds.has(String(item.id));
              return (
                <label
                  key={String(item.id)}
                  className={cn(
                    'flex cursor-pointer items-start gap-3 rounded-md px-3 py-2.5 text-sm transition-colors hover:bg-muted',
                    checked && 'bg-primary/10 text-primary',
                    selectionFull && !checked && 'cursor-not-allowed opacity-50',
                  )}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={selectionFull && !checked}
                    onChange={() => onToggle(item)}
                    className="mt-0.5 h-4 w-4 shrink-0 rounded border-gray-300"
                  />
                  <span className="min-w-0 flex-1 truncate" title={getLabel(item)}>
                    {getLabel(item)}
                  </span>
                </label>
              );
            })
          )}
        </div>
      </aside>

      <section className="min-h-[20rem] min-w-0 flex-1 overflow-y-auto bg-muted/20 p-4">
        {selectedItems.length === 0 ? (
          <div className="flex h-full min-h-[18rem] flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-background/70 text-center text-muted-foreground">
            <LayoutGrid className="h-10 w-10" />
            <div>
              <p className="font-medium text-foreground">
                {t('multi_display.empty_title', 'Select items to display')}
              </p>
              <p className="mt-1 text-sm">
                {t('multi_display.empty_description', 'Use the checkboxes to add items to this view.')}
              </p>
            </div>
          </div>
        ) : (
          <div className={cn('grid gap-4', gridColumnClasses[columns] || gridColumnClasses[2])}>
            {selectedItems.map((item) => (
              <article key={String(item.id)} className="min-w-0 overflow-hidden rounded-lg border bg-background shadow-sm">
                <header className="flex items-center justify-between gap-3 border-b px-4 py-3">
                  <h2 className="min-w-0 flex-1 truncate font-semibold" title={getLabel(item)}>
                    {getLabel(item)}
                  </h2>
                  <button
                    type="button"
                    className="shrink-0 text-xs text-muted-foreground hover:text-destructive"
                    onClick={() => onToggle(item)}
                  >
                    {t('common.remove', 'Remove')}
                  </button>
                </header>
                <div className="grid min-w-0 grid-cols-4 gap-3 p-3">
                  {renderItem(item)}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
