# coding=utf-8
"""Unit tests for as1.py."""
import copy
import re

from oauth_dropins.webutil import testutil

from .. import as1

LIKES = [{
  'verb': 'like',
  'author': {'id': 'tag:fake.com:person', 'numeric_id': '5'},
  'object': {'url': 'http://foo/like/5'},
}, {
  'verb': 'like',
  'author': {'id': 'tag:fake.com:6'},
  'object': {'url': 'http://bar/like/6'},
}]
REACTIONS = [{
  'id': 'tag:fake.com:apple',
  'verb': 'react',
  'content': '✁',
  'author': {'id': 'tag:fake.com:5'},
  'object': {'url': 'http://foo/like/5'},
}]
SHARES = [{
  'verb': 'share',
  'author': {'id': 'tag:fake.com:3'},
  'object': {'url': 'http://bar/like/3'},
}]
ACTIVITY = {
  'id': '1',
  'object': {
    'id': '1',
    'tags': LIKES + REACTIONS + SHARES,
  },
}
COMMENT = {
  'objectType': 'comment',
  'content': 'foo bar',
  'id': 'tag:fake.com:547822715231468_6796480',
  'published': '2012-12-05T00:58:26+00:00',
  'url': 'https://www.facebook.com/547822715231468?comment_id=6796480',
  'inReplyTo': [{
    'id': 'tag:fake.com:547822715231468',
    'url': 'https://www.facebook.com/547822715231468',
  }],
}
EVENT = {
  'id': 'tag:fake.com:246',
  'objectType': 'event',
  'displayName': 'Homebrew Website Club',
  'url': 'https://facebook.com/246',
  'author': {'displayName': 'Host', 'id': 'tag:fake.com,2013:666'},
}
RSVP_YES = {
  'id': 'tag:fake.com:246_rsvp_11500',
  'objectType': 'activity',
  'verb': 'rsvp-yes',
  'actor': {'displayName': 'Aaron P', 'id': 'tag:fake.com,2013:11500'},
  'url': 'https://facebook.com/246#11500',
}
RSVP_NO = {
  'objectType': 'activity',
  'verb': 'rsvp-no',
  'actor': {'displayName': 'Ryan B'},
  'url': 'https://facebook.com/246',
}
RSVP_MAYBE = {
  'id': 'tag:fake.com:246_rsvp_987',
  'objectType': 'activity',
  'verb': 'rsvp-maybe',
  'actor': {'displayName': 'Foo', 'id': 'tag:fake.com,2013:987'},
  'url': 'https://facebook.com/246#987',
}
INVITE = {
  'id': 'tag:fake.com:246_rsvp_555',
  'objectType': 'activity',
  'verb': 'invite',
  'actor': {'displayName': 'Host', 'id': 'tag:fake.com,2013:666'},
  'object': {'displayName': 'Invit Ee', 'id': 'tag:fake.com,2013:555'},
  'url': 'https://facebook.com/246#555',
}
RSVPS = [RSVP_YES, RSVP_NO, RSVP_MAYBE, INVITE]
EVENT_WITH_RSVPS = copy.deepcopy(EVENT)
EVENT_WITH_RSVPS.update({
  'attending': [RSVP_YES['actor']],
  'notAttending': [RSVP_NO['actor']],
  'maybeAttending': [RSVP_MAYBE['actor']],
  'invited': [INVITE['object']],
})
LIKE = {
  'id': 'tag:fake.com:001_liked_by_222',
  'url': 'http://plus.google.com/001#liked-by-222',
  'objectType': 'activity',
  'verb': 'like',
  'object': {'url': 'http://plus.google.com/001'},
  'author': {
    'kind': 'plus#person',
    'id': 'tag:fake.com:222',
    'displayName': 'Alice',
    'url': 'https://profiles.google.com/alice',
    'image': {'url': 'https://alice/picture'},
  },
}
RESHARER = {
  'kind': 'plus#person',
  'id': 'tag:fake.com:444',
  'displayName': 'Bob',
  'url': 'https://plus.google.com/bob',
  'image': {'url': 'https://bob/picture'},
}


class As1Test(testutil.TestCase):

  def test_is_public(self):
    for obj in ({'to': [{'objectType': 'unknown'}]},
                {'to': [{'objectType': 'unknown'},
                        {'objectType': 'unknown'}]},
                {'to': [{'alias': 'xyz'},
                        {'objectType': 'unknown'}]},
               ):
      self.assertIsNone(as1.is_public(obj), repr(obj))
      self.assertIsNone(as1.is_public({'object': obj}), repr(obj))

    for obj in ({},
                {'privacy': 'xyz'},
                {'to': []},
                {'to': [{}]},
                {'to': [{'objectType': 'group'}]},
                {'to': [{'objectType': 'group', 'alias': '@unlisted'}]},
                {'to': [{'objectType': 'group', 'alias': '@public'}]},
                {'to': [{'objectType': 'group', 'alias': '@private'},
                        {'objectType': 'group', 'alias': '@public'}]},
                {'to': [{'alias': '@public'},
                        {'alias': '@private'}]},
               ):
      self.assertTrue(as1.is_public(obj), repr(obj))
      self.assertTrue(as1.is_public({'object': obj}), repr(obj))

    for obj in ({'to': [{'objectType': 'group', 'alias': '@private'}]},
                {'to': [{'objectType': 'group', 'alias': 'xyz'}]},
                {'to': [{'alias': 'xyz'}]},
                {'to': [{'alias': 'xyz'},
                        {'alias': '@private'}]},
                {'to': [{'objectType': 'group'},
                        {'alias': 'xyz'},
                        {'alias': '@private'}]},
               ):
      self.assertFalse(as1.is_public(obj), repr(obj))
      self.assertFalse(as1.is_public({'object': obj}), repr(obj))

  def test_activity_changed(self):
    fb_post = copy.deepcopy(ACTIVITY)
    fb_post['object']['updated'] = '2016-01-02T00:00:00+00:00'
    fb_post_edited = copy.deepcopy(fb_post)
    fb_post_edited['object']['updated'] = '2016-01-02T00:58:26+00:00'

    fb_comment = COMMENT
    fb_comment_edited = copy.deepcopy(fb_comment)
    fb_comment_edited['published'] = '2016-01-02T00:58:26+00:00'

    gp_like = LIKE
    gp_like_edited = copy.deepcopy(gp_like)
    gp_like_edited['author'] = RESHARER

    for before, after in (({}, {}),
                          ({'x': 1}, {'y': 2}),
                          ({'to': None}, {'to': ''}),
                          (fb_post, fb_post_edited),
                          (fb_comment, fb_comment_edited),
                          (gp_like, gp_like_edited)):
      self.assertFalse(as1.activity_changed(before, after, log=True),
                       f'{before}\n{after}')

    fb_comment_edited_inReplyTo = copy.deepcopy(fb_comment_edited)
    fb_comment_edited_inReplyTo['inReplyTo'].append({
      'id': 'tag:fake.com:000000000000000',
      'url': 'https://www.facebook.com/000000000000000',
    })
    fb_comment_edited['content'] = 'new content'
    gp_like_edited['to'] = [{'objectType':'group', 'alias':'@private'}]

    fb_invite = INVITE
    self.assertEqual('invite', fb_invite['verb'])
    fb_rsvp = RSVP_YES

    for before, after in ((fb_comment, fb_comment_edited),
                          (fb_comment, fb_comment_edited_inReplyTo),
                          (gp_like, gp_like_edited),
                          (fb_invite, fb_rsvp)):
      self.assertTrue(as1.activity_changed(before, after, log=True),
                      f'{before}\n{after}')

  def test_append_in_reply_to(self):
    fb_comment_before = copy.deepcopy(COMMENT)
    fb_comment_after_same = copy.deepcopy(fb_comment_before)
    as1.append_in_reply_to(fb_comment_before,fb_comment_after_same)
    self.assertEqual(COMMENT, fb_comment_before)
    self.assertEqual(COMMENT, fb_comment_after_same)

    fb_comment_after_diff = copy.deepcopy(fb_comment_before)
    fb_comment_after_targ = copy.deepcopy(fb_comment_before)
    fb_comment_after_diff['inReplyTo'] = ['new']
    fb_comment_after_targ['inReplyTo'] = fb_comment_after_diff.get('inReplyTo')+fb_comment_before.get('inReplyTo')
    as1.append_in_reply_to(fb_comment_before,fb_comment_after_diff)
    self.assertEqual(fb_comment_after_targ,fb_comment_after_diff)

  def test_add_rsvps_to_event(self):
    event = copy.deepcopy(EVENT)
    as1.add_rsvps_to_event(event, [])
    self.assert_equals(EVENT, event)

    as1.add_rsvps_to_event(event, RSVPS)
    self.assert_equals(EVENT_WITH_RSVPS, event)

  def test_get_rsvps_from_event(self):
    self.assert_equals([], as1.get_rsvps_from_event(EVENT))
    self.assert_equals(RSVPS, as1.get_rsvps_from_event(EVENT_WITH_RSVPS))

  def test_get_rsvps_from_event_bad_id(self):
    event = copy.deepcopy(EVENT)
    for id in None, 'not_a_tag_uri':
      event['id'] = id
      self.assert_equals([], as1.get_rsvps_from_event(event))
  def check_original_post_discovery(self, obj, originals, mentions=None,
                                    **kwargs):
    got = as1.original_post_discovery({'object': obj}, **kwargs)
    self.assert_equals(originals, got[0])
    self.assert_equals(mentions or [], got[1])

  def test_original_post_discovery(self):
    check = self.check_original_post_discovery

    # noop
    obj = {
      'objectType': 'article',
      'displayName': 'article abc',
      'url': 'http://example.com/article-abc',
      'tags': [],
    }
    check(obj, [])

    # attachments and tags become upstreamDuplicates
    check({'tags': [{'url': 'http://a', 'objectType': 'article'},
                    {'url': 'http://b'}],
           'attachments': [{'url': 'http://c', 'objectType': 'mention'}]},
          ['http://a/', 'http://b/', 'http://c/'])

    # non-article objectType
    urls = [{'url': 'http://x.com/y', 'objectType': 'image'}]
    check({'attachment': urls}, [])
    check({'tags': urls}, [])

    # permashortcitations
    check({'content': 'x (not.at end) y (at.the end)'}, ['http://at.the/end'])

    # merge with existing tags
    obj.update({
      'content': 'x http://baz/3 yyyy',
      'attachments': [{'objectType': 'article', 'url': 'http://foo/1'}],
      'tags': [{'objectType': 'article', 'url': 'http://bar/2'}],
    })
    check(obj, ['http://foo/1', 'http://bar/2', 'http://baz/3'])

    # links become upstreamDuplicates
    check({'content': 'asdf http://first ooooh http://second qwert'},
          ['http://first/', 'http://second/'])
    check({'content': 'x http://existing y',
           'upstreamDuplicates': ['http://existing']},
          ['http://existing/'])

    # leading parens used to cause us trouble
    check({'content': 'Foo (http://snarfed.org/xyz)'}, ['http://snarfed.org/xyz'])

    # don't duplicate http and https
    check({'content': 'X http://mention Y https://both Z http://both2',
           'upstreamDuplicates': ['http://upstream', 'http://both', 'https://both2']},
          ['http://upstream/', 'https://both/', 'https://both2/', 'http://mention/'])

    # don't duplicate PSCs and PSLs with http and https
    for scheme in 'http', 'https':
      url = scheme + '://foo.com/1'
      check({'content': 'x (foo.com/1)', 'tags': [{'url': url}]}, [url])

    check({'content': 'x (foo.com/1)', 'attachments': [{'url': 'http://foo.com/1'}]},
          ['http://foo.com/1'])
    check({'content': 'x (foo.com/1)', 'tags': [{'url': 'https://foo.com/1'}]},
          ['https://foo.com/1'])

    # exclude ellipsized URLs
    for ellipsis in '...', '…':
      url = 'foo.com/1' + ellipsis
      check({'content': f'x ({url})',
             'attachments': [{'objectType': 'article', 'url': 'http://' + url}]},
            [])

    # exclude ellipsized PSCs and PSLs
    for separator in '/', ' ':
      for ellipsis in '...', '…':
        check({'content': f'x (ttk.me{separator}123{ellipsis})'}, [])

    # domains param
    obj = {
      'content': 'x http://me.x.y/a y',
      'upstreamDuplicates': ['http://me.x.y/b'],
      'attachments': [{'url': 'http://me.x.y/c'}],
      'tags': [{'url': 'http://me.x.y/d'}],
    }
    links = ['http://me.x.y/a', 'http://me.x.y/b', 'http://me.x.y/c', 'http://me.x.y/d']
    check(obj, links)
    for domains in [], ['me.x.y'], ['foo', 'x.y']:
      check(obj, links, domains=domains)

    check(obj, [], mentions=links, domains=['e.x.y', 'not.me.x.y', 'alsonotme'])

    # utm_* query params
    check({'content': 'asdf http://other/link?utm_source=x&utm_medium=y&a=b qwert',
           'upstreamDuplicates': ['http://or.ig/post?utm_campaign=123']},
          ['http://or.ig/post', 'http://other/link?a=b'])

    # invalid URLs
    check({'upstreamDuplicates': [''],
           'tags': [{'url': 'http://bad]'}]},
          [])

    # bookmarks should include targetUrl
    check({'targetUrl': 'http://or.ig/'}, ['http://or.ig/'])

  def test_original_post_discovery_max_redirect_fetches(self):
    self.expect_requests_head('http://other/link', redirected_url='http://a'
                              ).InAnyOrder()
    self.expect_requests_head('http://sho.rt/post', redirected_url='http://b'
                              ).InAnyOrder()
    self.mox.ReplayAll()

    obj = {
      'content': 'asdf http://other/link qwert',
      'upstreamDuplicates': ['http://sho.rt/post', 'http://next/post'],
    }
    self.check_original_post_discovery(
      obj, ['http://a/', 'http://b/', 'http://next/post'], max_redirect_fetches=2)

  def test_original_post_discovery_follow_redirects_false(self):
    self.expect_requests_head('http://other/link',
                              redirected_url='http://other/link/redirected'
                             ).MultipleTimes()
    self.expect_requests_head('http://sho.rt/post',
                              redirected_url='http://or.ig/post/redirected'
                             ).MultipleTimes()
    self.mox.ReplayAll()

    obj = {
      'content': 'asdf http://other/link qwert',
      'upstreamDuplicates': ['http://sho.rt/post'],
    }
    originals = ['http://sho.rt/post', 'http://or.ig/post/redirected']
    mentions = ['http://other/link', 'http://other/link/redirected']

    check = self.check_original_post_discovery
    check(obj, originals + mentions)
    check(obj, originals, mentions=mentions, domains=['or.ig'])
    check(obj, ['http://or.ig/post/redirected', 'http://other/link/redirected'],
          include_redirect_sources=False)

  def test_original_post_discovery_excludes(self):
    """Should exclude reserved hosts, non-http(s) URLs, and missing domains."""
    obj = {
      'content': 'foo',
      'upstreamDuplicates': [
        'http://sho.rt/post',
        # local
        'http://localhost',
        'http://other/link',
        'http://y.local/path'
        # reserved
        'https://x.test/',
        # not http
        'file://foo.com/Ryan/.npmrc'
        'git@github.com:snarfed/granary.git',
        '/home/ryan/foo',
        'mailto:x@y.z',
        # missing domain
        'http:///foo/bar',
        'file:///Users/Ryan/.npmrc',
      ],
    }
    self.check_original_post_discovery(
      obj, ['http://sho.rt/post'], include_reserved_hosts=False)

  def test_original_post_discovery_exclude__hosts(self):
    obj = {
      'content': 'http://other/link https://x.test/ http://y.local/path',
      'upstreamDuplicates': ['http://localhost', 'http://sho.rt/post'],
    }
    self.check_original_post_discovery(
      obj, ['http://sho.rt/post'], include_reserved_hosts=False)

    # TODO: missing tests
