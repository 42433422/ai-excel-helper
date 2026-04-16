/** English UI (partial keys fall back to zh-CN via vue-i18n fallbackLocale) */
export default {
  intro: {
    app: {
      apiHealthWarn: 'MODstore API is reachable but the health check did not return ok.',
      apiConnFail:
        'Cannot reach MODstore API (default 127.0.0.1:8765). Run start-modstore.bat in this folder, or confirm Vite proxies /api to modstore_server.',
    },

    appTagline:
      'Local workbench for XCAGI extension packs (Mods): store, edit, validate, and integrate with XCAGI / FHD.',

    navTitle: {
      library: 'Mod library: browse, import/export, and sync',
      author: 'Authoring: manifest fields, host /api routes, blueprint conventions',
      debug: 'Debug: sandbox folder, XCAGI load status, single-mod push',
      settings: 'Paths & sync: library root, XCAGI root, backend URL, FHD shell JSON export',
    },

    navShort: {
      library: 'Library',
      author: 'Author',
      debug: 'Debug',
      settings: 'Paths',
    },

    common: {
      close: 'Dismiss',
      langZh: '中文',
      langEn: 'English',
    },

    home: {
      title: 'Mod library',
      leadBefore:
        'All Mods under the library folder: each directory is a pack with manifest.json — validate, edit, import ZIP, and push to XCAGI/mods for the host to load at startup. For Chinese field help or merging /api routes from the host OpenAPI, open',
      leadAfter: '.',
      authorLink: 'Authoring guide',
      leadTail:
        'Pushing to XCAGI/mods or using a XCAGI_MODS_ROOT sandbox from the Debug page works the same as before.',
      monitorTitle: 'XCAGI mods on disk',
      monitorSub: 'Packs under the configured XCAGI root /mods (same target as Push)',
      monitorPath: 'mods path',
      monitorEmpty: 'No deployed mod folders yet',
      monitorLoading: 'Scanning…',
      monitorErr: 'Scan failed',
      monitorPrimary: 'PRIMARY',
      monitorFooter: 'Runtime load status: Debug page',
      currentPrimaryLabel: 'Primary mod: ',
      currentPrimaryLine: '{name} ({id})',
      currentPrimaryNone:
        'No primary mod: no manifest has primary: true. The host uses this flag for the “main” extension badge/sidebar emphasis. Set it in a manifest or use Debug → focus primary.',
      currentPrimaryMany: 'Warning: {count} mods are marked primary; keep only one.',
      monitorCurrentTitle: 'Primary',
      gridHint: 'Click a card to open validation and editing (same id as the deployed list on the right when in sync).',
      monitorRowLinkTitle: 'Open this Mod in the library',
    },

    author: {
      fallbackPage:
        'Field conventions and blueprint habits for writing Mods. After “Merge host /api routes”, MODstore downloads openapi.json from the backend URL in Paths & sync and lists only /api paths for comparison with your blueprints.',
      manifestSection:
        'Common manifest fields below. “Required” means validation strongly recommends filling the value.',
      blueprintSection:
        'Implement register_blueprints(app, mod_id) in a Python module and point manifest.backend.entry to that module name.',
      openapiSection:
        'Table is a short list of host HTTP routes; parameters, bodies, and auth are defined in the host /openapi.json.',
      runtimeSection:
        'Deployment targets, sandbox env vars, and FHD shell menu export keywords for copy/paste into docs or scripts.',
      title: 'Authoring guide',
      subHint:
        'Set the host backend URL under Paths & sync, then refresh bundled help or merge /api routes from openapi.json.',
      btnRefresh: 'Reload bundled surface',
      btnMerge: 'Merge host /api routes',
      btnMergeLoading: 'Fetching host OpenAPI…',
      loading: 'Loading…',
      manifestTitle: 'Manifest fields',
      blueprintTitle: 'Backend blueprint convention',
      openapiTitle: 'Host API summary (OpenAPI)',
      openapiCount:
        '{n} path(s) with /api prefix; see the host /openapi.json for the full definition.',
      thPath: 'Path',
      thMethod: 'Method',
      hostOpenapiTitle: 'Host OpenAPI',
      runtimeTitle: 'Runtime & debug',
      requiredPill: 'Required',
      examplePrefix: 'e.g.',
      flashHostOpenapiFail: 'Bundled surface loaded; host OpenAPI fetch failed (see below).',
      flashMergedRoutes: 'Merged {count} /api route(s).',
    },

    settings: {
      lead:
        'Library root is where MODstore keeps all Mod sources (defaults to library/ in the project). XCAGI root is used for push/pull into XCAGI/mods. Backend URL is used by the Debug page and authoring proxy. Export FHD JSON feeds GET /api/mods in this repo’s FHD shell.',
    },

    debug: {
      lead:
        'Sandbox creates a mods directory with a single Mod; set XCAGI_MODS_ROOT to it and restart the XCAGI backend to debug without touching the main mods folder. JSON below is a proxied /api/mods/loading-status response.',
    },

    notFound: {
      lead: 'This URL has no page. Return to the Mod library below.',
    },

    modDetail: {
      overviewHint:
        'Overview shows API/backend entry, manifest config, workflow staff, and frontend menu. Use Edit for basics; JSON for the full structure.',
      em: '—',
      back: '← Back to list',
      loading: 'Loading…',
      validationOk: 'Valid',
      validationWarn: 'Warnings',
      exportZip: 'Export ZIP',
      pushXcagi: 'Push to XCAGI',
      delete: 'Delete',
      warningsTitle: 'Validation notes',
      tabsAria: 'Mod detail sections',
      tabOverview: 'Overview',
      tabEdit: 'Edit',
      tabJson: 'JSON',
      tabFiles: 'Files',
      cardApiTitle: 'API & backend',
      subHooks: 'Hooks',
      routesPrefix: 'Routes · ',
      bpScanning: 'Scanning…',
      thFunction: 'Function',
      thPath: 'Path',
      thMethod: 'Method',
      bpNoRoutes: 'No @route decorators found.',
      cardConfigTitle: 'Config',
      configHintBefore: 'Host database settings live in XCAGI; this section shows only the manifest ',
      configHintAfter: ' object.',
      noConfig: 'No config',
      cardWorkflowTitle: 'Workflow / staff',
      notConfigured: 'Not configured',
      cardMenuTitle: 'Frontend menu',
      thMenuId: 'Menu id',
      thMenuLabel: 'Label',
      thMenuPath: 'Path',
      thMenuIcon: 'Icon',
      noMenu: 'No menu',
      editBasicTitle: 'Basics',
      editHint: 'Edit complex fields on the JSON tab.',
      labelId: 'id (must match folder name)',
      labelVersion: 'Version',
      labelName: 'Name',
      labelAuthor: 'Author',
      labelDescription: 'Description',
      labelPrimary: 'primary (main mod)',
      btnSaveManifest: 'Save to manifest',
      jsonLabel: 'Full JSON (keep id matching the folder name)',
      btnSaveJson: 'Save JSON',
      filesHint:
        'Click a text file to edit in-browser (same allowlist as the server: .py .json .vue .ts .js .css .md .txt .html, etc.).',
      noFiles: 'No files or scan empty.',
      modalClose: 'Close',
      modalSave: 'Save',
      modalSaving: 'Saving…',
      msgSaved: 'Saved',
      msgSavedWithWarnings: 'Saved (see warnings above)',
      msgFileSaved: 'File saved',
      msgSavedFileWarn: 'Saved (manifest note: {hint})',
      jsonParseErr: 'Invalid JSON: {msg}',
      msgDeployed: 'Deployed: {list}',
      confirmDelete: 'Delete mod “{id}” from the library? This cannot be undone.',
      cardFhdTokensTitle: 'FHD database tokens',
      fhdReadTokenLabel: 'Read token (X-FHD-Db-Read-Token)',
      fhdWriteTokenLabel: 'Write token (X-FHD-Db-Write-Token)',
      fhdTokensHint:
        'Same semantics as FHD env FHD_DB_READ_TOKEN / FHD_DB_WRITE_TOKEN; stored in manifest.config for your deploy pipeline to sync into the host. Do not commit secrets to public repos.',
      fhdTokenSet: 'Set ({n} chars)',
      fhdTokenUnset: 'Not set',
      fhdColManifest: 'In Mod (manifest.config)',
      fhdColHost: 'Host FHD (environment)',
      fhdHostReadYes: 'Read: configured',
      fhdHostReadNo: 'Read: not configured',
      fhdHostWriteYes: 'Write: configured',
      fhdHostWriteNo: 'Write: not configured',
      fhdHostFetchErr: 'Cannot reach host (check Paths & sync backend URL, e.g. FHD :8000)',
      cardWalletTitle: 'Wallet secret',
      walletSecretLabel: 'Secret (API key / private key, etc.)',
      walletHint:
        'Stored as manifest.config.wallet_secret; read by host or on-chain services. Do not commit to public repos. Independent of FHD DB tokens.',
    },

    fieldKindLabel: {
      string: 'Text',
      boolean: 'Yes/No',
      array: 'List',
      object: 'Object',
      stringList: 'String list',
    },
  },
}
