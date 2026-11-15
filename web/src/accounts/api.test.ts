import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ApiError, errorMessage, opensWithoutLogin, tokenFromHash } from './api.ts'

test('every server error from #35 has plain words', () => {
  const msg = (status: number, detail = '', retry: number | null = null) =>
    errorMessage(new ApiError(status, detail, retry))
  assert.equal(msg(401, 'wrong email or password'), 'Wrong email or password.')
  assert.equal(msg(401, 'not logged in'), 'Please log in again.')
  assert.match(msg(403), /Only the person who added/)
  assert.equal(msg(404, 'that person needs to sign up first'), 'That person needs to sign up first.')
  assert.match(msg(409, 'an account with that email exists'), /Log in instead/)
  assert.match(msg(422), /8 characters/)
  assert.equal(msg(429, '', 30), 'Too many attempts. Try again in 30 seconds.')
  assert.equal(msg(429, '', 600), 'Too many attempts. Try again in 10 minutes.')
  assert.equal(msg(429), 'Too many attempts. Try again later.')
  assert.match(msg(503), /Live calls still work/)
  assert.match(msg(0), /Can't reach Aegis/)
})

test('pairing token comes only from a plausible #hash', () => {
  assert.equal(tokenFromHash('#abcDEF123_-abcDEF123'), 'abcDEF123_-abcDEF123')
  assert.equal(tokenFromHash(''), null)
  assert.equal(tokenFromHash('#short'), null)
  assert.equal(tokenFromHash('#<script>alert(1)</script>xxxxxxxx'), null)
})

test('a sample or a call link with its token opens without a login, nothing else does', () => {
  assert.equal(opensWithoutLogin('?fixture=demo-bank'), true)
  // The runbook's judges' link: /evidence?session=<id>&token=<elder token>, also with accounts offline.
  assert.equal(opensWithoutLogin('?session=abc&token=xyz'), true)
  assert.equal(opensWithoutLogin('?session=abc'), false)
  assert.equal(opensWithoutLogin('?token=xyz'), false)
  assert.equal(opensWithoutLogin('?session=abc&token='), false)
  assert.equal(opensWithoutLogin(''), false)
})
