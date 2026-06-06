type ViewLoader = () => Promise<{ default: unknown }>

export const hostViewGlob = import.meta.glob('../views/**/*.vue') as Record<string, ViewLoader>
