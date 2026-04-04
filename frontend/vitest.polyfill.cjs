const cryptoMod = require('node:crypto');

const webcrypto = cryptoMod && cryptoMod.webcrypto ? cryptoMod.webcrypto : null;
if (webcrypto) {
  if (typeof cryptoMod.getRandomValues !== 'function') {
    cryptoMod.getRandomValues = webcrypto.getRandomValues.bind(webcrypto);
  }
  if (typeof cryptoMod.randomUUID !== 'function' && typeof webcrypto.randomUUID === 'function') {
    cryptoMod.randomUUID = webcrypto.randomUUID.bind(webcrypto);
  }

  if (!globalThis.crypto) {
    Object.defineProperty(globalThis, 'crypto', {
      value: webcrypto,
      configurable: true,
    });
  } else {
    if (typeof globalThis.crypto.getRandomValues !== 'function') {
      globalThis.crypto.getRandomValues = webcrypto.getRandomValues.bind(webcrypto);
    }
    if (typeof globalThis.crypto.randomUUID !== 'function' && typeof webcrypto.randomUUID === 'function') {
      globalThis.crypto.randomUUID = webcrypto.randomUUID.bind(webcrypto);
    }
    if (typeof globalThis.crypto.subtle === 'undefined' && webcrypto.subtle) {
      globalThis.crypto.subtle = webcrypto.subtle;
    }
  }
}
