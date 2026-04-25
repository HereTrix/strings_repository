let navigateFunc: ((path: string, options?: object) => void) | null = null;

export const setNavigate = (fn: typeof navigateFunc) => {
    navigateFunc = fn;
};

export const navigate = (path: string, options?: object) => {
    navigateFunc?.(path, options);
};
