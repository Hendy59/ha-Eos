import test from 'node:test';
import assert from 'node:assert/strict';
import { createTranslator, supportedLanguages } from '../../custom_components/helios/panel/helios-i18n.js';

test('provides the supported panel languages', () => {
  assert.deepEqual(supportedLanguages, ['en', 'de', 'pl']);
});

test('formats translated messages and falls back by language family', () => {
  assert.equal(createTranslator('de-DE')('duplicateId', { id: 'living-room' }), 'Doppelte ID: living-room');
  assert.equal(createTranslator('pl')('pageDefaultName', { number: 2 }), 'Strona 2');
  assert.equal(createTranslator('fr')('save'), 'Save');
});

test('uses the key when a message is not defined', () => {
  assert.equal(createTranslator('de')('missing.key'), 'missing.key');
});

test('translates card types, form fields and action options', () => {
  const de = createTranslator('de');
  assert.equal(de('type.energy'), 'Energie (PV, Haus, Batterie)');
  assert.equal(de('field.confirm_enabled'), 'Vor Ausführung fragen');
  assert.equal(de('action.turn_on'), 'Einschalten');
  assert.equal(de('unknown.label', {}, 'Fallback'), 'Fallback');
});
