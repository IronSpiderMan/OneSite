// A successful model write may also change related models through inline relations or hooks.
// Lists remember this revision so returning to another model never reuses a pre-write page.
let dataRevision = 0;

export const getDataRevision = () => dataRevision;
export const markDataChanged = () => { dataRevision += 1; };

if (typeof window !== 'undefined') {
    window.addEventListener('onesite:import-complete', (event: Event) => {
        if (!(event as CustomEvent).detail?.error) markDataChanged();
    });
}
