# webui/

React SPA built with TypeScript and webpack. The Django `webui` app serves only the compiled `index.html` shell — all real logic is in `src/`.

## Tech Stack

- **React 19** + **TypeScript 5**
- **React Router v7** — client-side routing, all routes defined in `App.tsx`
- **React Bootstrap 2** + **Bootstrap 5** — UI components and theming
- **react-bootstrap-typeahead** — typeahead/autocomplete inputs
- **react-hook-form** — form state management
- **react-infinite-scroll-component** — infinite scroll pagination
- **webpack 5** — build, with `ts-loader`

## Build

```bash
npm ci
npm run build      # production (hashed filenames, vendor chunks)
npm run watch      # dev watch mode
```

Output: `webui/static/site/` (JS/CSS) and `webui/templates/site/index.html` (Django template). Django's collectstatic picks these up automatically.

## Source Layout

```
src/
  components/     # UI components, grouped by feature
    App.tsx       # root component, defines all routes
    Auth/         # PrivateRoute (auth guard)
    Bundles/      # bundle management
    History/      # change history
    Languages/    # language list and add-language modal
    pages/        # top-level route pages (Login, Home, Activate, PageNotFound)
    Profile/      # user profile screens
    Project/      # project page and sub-components
    shell/        # NavBar, Logout — chrome present on all authenticated screens
    StringTokens/ # token list, scope management, scope gallery
    Translation/  # translation pages and list items
    UI/           # shared generic components (alerts, filters, tags, etc.)
  hooks/          # usePagination, useTheme
  types/          # plain TypeScript interfaces mirroring Django serializer output
  utils/          # network, navigation, history helpers
  styles/         # typeahead-dark.css
  declarations.d.ts
  index.tsx
```

## API Communication

All network calls go through three functions in `src/utils/network.tsx`:
- `http<T>(request)` — JSON request/response
- `upload<T>(request)` — multipart FormData (file imports)
- `download(request)` — blob download, extracts filename from `content-disposition`

Auth token is read from `localStorage` key `"auth"` and sent as the `Authorization` header. On 401, the token is cleared and the user is redirected to `/login` via the imperative `navigate()` singleton in `src/utils/navigation.ts`.

API error responses have shape `{ error: string }`.

## Routing

Routes are defined in `App.tsx` using `React.lazy()` for code splitting. Protected routes use `Auth/PrivateRoute`. The `ProjectPage` route uses an optional `:tab?` param — the active tab is reflected in the URL.

## Theming

Light/dark toggle via Bootstrap 5's native `data-bs-theme` attribute on `<html>`. Persisted to `localStorage` key `"theme"`. Initialized in `index.tsx` before React mounts to avoid flash. Managed by `src/hooks/useTheme.ts`.

No CSS modules, no Tailwind, no Sass. Custom CSS only in `src/styles/typeahead-dark.css`.

## Pagination

`src/hooks/usePagination.ts` — generic limit/offset hook. Frontend page size is `PAGE_LIMIT = 20` (sent as the `limit` query param). Works with `react-infinite-scroll-component`.

## Types

Plain TypeScript interfaces in `src/types/` (`.ts` files, no JSX). These mirror Django serializer output exactly. Update them when serializer shapes change.

Global ambient declarations (e.g. module stubs) live in `src/declarations.d.ts`.

## Scopes

A Scope groups a subset of string tokens within a project and can have reference images attached. Key components (all in `StringTokens/`):

- `ScopeManager.tsx` — unified CRUD component for scopes (create, edit, delete, image upload, token assignment). Renders inline when used as a tab inside `ProjectPage`; renders inside a `Modal` when `onHide` is provided (used from `StringTokensList`).
- `ScopeTokenAssigner.tsx` — assigns/removes string tokens from a scope; uses infinite scroll and `TagFilter` for filtering.
- `ScopesGallery.tsx` — card grid of scopes for a project; fires `onScopeSelect` callback when the user picks one (used in `Translation/LanguageTranslationsPage`).

Model: `src/types/Scope.ts` — `Scope` (id, name, description, images, token_count, token_ids) and `ScopeImage` (id, url, created_at).

There is no dedicated `/scopes` route — scopes are reached via the `tab` param on `/project/:id/:tab?`.

## Verification

After making changes, run from `webui/`:

```bash
npm run typecheck   # fast type check, no emit
npm test            # Jest unit tests
```

UI changes must be tested manually — there are no component or e2e tests.

## Tests

Jest + Babel (TypeScript via `@babel/preset-typescript`). Test files live in `__tests__/` subdirectories next to the code they cover, named `*.test.ts`.

Current coverage:
- `src/types/__tests__/StringToken.test.ts` — status helpers
- `src/types/__tests__/Translation.test.ts` — status helpers, plural form order, editable statuses
- `src/hooks/__tests__/usePagination.test.ts` — pagination state logic

When adding component tests, install `@testing-library/user-event` and add `setupFilesAfterEach: ['@testing-library/jest-dom']` to `jest.config.js`.

## Component Conventions

- One directory per feature area under `components/`
- Page-level route components live in `components/pages/`
- App chrome (NavBar, Logout) lives in `components/shell/`
- Page-level components are named `*Page.tsx`; modal components are named `*Modal.tsx`
- No global state library — data is fetched and held in component state, passed down via props
