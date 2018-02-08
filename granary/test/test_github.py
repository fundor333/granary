# coding=utf-8
"""Unit tests for github.py.
"""
import copy
import json

import mox
from oauth_dropins import github as oauth_github
from oauth_dropins.webutil import testutil
from oauth_dropins.webutil import util

from granary import appengine_config
from granary import github
from granary import source

# test data
def tag_uri(name):
  return util.tag_uri('github.com', name)

USER = {  # GitHub
  'login': 'snarfed',
  'resourcePath': '/snarfed',
  'url': 'https://github.com/snarfed',
  'avatarUrl': 'https://avatars2.githubusercontent.com/u/778068?v=4',
  'id': 'MDQ6VXNlcjc3ODA2OA==',
  'email': 'github@ryanb.org',
  'location': 'San Francisco',
  'name': 'Ryan Barrett',
  'websiteUrl': 'https://snarfed.org/',
  'bio': 'foo https://brid.gy/\r\nbar',  # may be null
  'bioHTML': """\
<div>foo <a href="https://brid.gy/" rel="nofollow">https://brid.gy/</a>
bar</div>""",
  'company': '@bridgy',
  'companyHTML': '<div><a href="https://github.com/bridgy" class="user-mention">bridgy</a></div>',
  'createdAt': '2011-05-10T00:39:24Z'
}
ACTOR = {  # ActivityStreams
  'objectType': 'person',
  'displayName': 'Ryan Barrett',
  'image': {'url': 'https://avatars2.githubusercontent.com/u/778068?v=4'},
  'id': tag_uri('MDQ6VXNlcjc3ODA2OA=='),
  'published': '2011-05-10T00:39:24+00:00',
  'url': 'https://snarfed.org/',
  'urls': [
    {'value': 'https://snarfed.org/'},
    {'value': 'https://brid.gy/'},
  ],
  'username': 'snarfed',
  'email': 'github@ryanb.org',
  'description': 'foo https://brid.gy/\r\nbar',
  'summary': 'foo https://brid.gy/\r\nbar',
  'location': {'displayName': 'San Francisco'},
  }
ISSUE = {  # GitHub
  'id': 'MDU6SXNzdWUyOTI5MDI1NTI=',
  'number': 6824,
  'url': 'https://github.com/metabase/metabase/issues/6824',
  'resourcePath': '/metabase/metabase/issues/6824',
  'repository': {
    'id': 'MDEwOlJlcG9zaXRvcnkzMDIwMzkzNQ=='
  },
  'author': {
    'avatarUrl': 'https://avatars2.githubusercontent.com/u/778068?v=4',
    'login': 'snarfed',
    'resourcePath': '/snarfed',
    'url': 'https://github.com/snarfed'
  },
  'title': 'an issue title',
  # note that newlines are \r\n in body but \n in bodyHTML and bodyText
  'body': """\
foo bar baz\r
[link](http://www.proficiencylabs.com/)\r
@user mention\r
hash: bf0076f377aeb9b1981118b6dd1e23779bd54502\r
issue: #123\r
""",
  'bodyHTML': """\
<p>foo bar baz
<a href="http://www.proficiencylabs.com/" rel="nofollow">link</a>
<a href="https://github.com/dshanske" class="user-mention">@user</a> mention
hash: <a href=\"https://github.com/pfefferle/wordpress-semantic-linkbacks/commit/bf0076f377aeb9b1981118b6dd1e23779bd54502\" class=\"commit-link\"><tt>bf0076f</tt></a>
issue: TODO
</p>""",
  'bodyText': """\
foo bar baz
link
@user mention
hash: bf0076f377aeb9b1981118b6dd1e23779bd54502
issue: #123
""",
  'state': 'OPEN',
  'closed': False,
  'locked': False,
  'closedAt': None,
  'createdAt': '2018-01-30T19:11:03Z',
  'lastEditedAt': None,
  'publishedAt': '2018-01-30T19:11:03Z'
}
COMMENT = {  # GitHub
  'id': 'MDEwOlNQ==',
  'url': 'https://github.com/foo/bar/123#issuecomment-456',
  'from': {
    'name': 'Ryan Barrett',
    'id': '212038'
  },
  'message': 'cc Sam G, Michael M',
  'message_tags': [{
    'id': '695687650',
    'name': 'Michael Mandel',
    'type': 'user',
    'offset': 10,
    'length': 9,
  }],
  'created_time': '2012-12-05T00:58:26+0000',
  'privacy': {'value': 'FRIENDS'},
}

COMMENT_OBJ = {  # ActivityStreams
    'objectType': 'comment',
    # 'author': {
    #   'objectType': 'person',
    #   'id': tag_uri('212038'),
    #   'numeric_id': '212038',
    #   'displayName': 'Ryan Barrett',
    #   'image': {'url': 'https://graph.github.com/v2.10/212038/picture?type=large'},
    #   'url': 'https://www.github.com/212038',
    # },
    'content': 'i have something to say here',
    'id': tag_uri('xyz'),
    'published': '2012-12-05T00:58:26+00:00',
    'url': 'https://github.com/foo/bar/pull/123#comment-xyz',
    'inReplyTo': [{
      'url': 'https://github.com/foo/bar/pull/123',
    }],
    # 'to': [{'objectType':'group', 'alias':'@private'}],
    # 'tags': [{
    #     'objectType': 'person',
    #     'id': tag_uri('221330'),
    #     'url': 'https://www.github.com/221330',
    #     'displayName': 'Sam G',
    #     'startIndex': 3,
    #     'length': 5,
    # }],
}
ISSUE_OBJ = {  # ActivityStreams
  'objectType': 'image',
  'author': {
    'objectType': 'person',
    'id': tag_uri('212038'),
    'numeric_id': '212038',
    'displayName': 'Ryan Barrett',
    'image': {'url': 'https://graph.github.com/v2.10/212038/picture?type=large'},
    'url': 'https://www.github.com/212038',
    },
  'content': 'Checking another side project off my list. portablecontacts-unofficial is live! &amp;3 Super Happy Block Party Hackathon, &gt;\o/&lt; Daniel M.',
  'id': tag_uri('10100176064482163'),
  'fb_id': '212038_10100176064482163',
  'published': '2012-03-04T18:20:37+00:00',
  'updated': '2012-03-04T19:08:16+00:00',
  'url': 'https://www.github.com/212038/posts/10100176064482163',
  'image': {'url': 'https://fbcdn-photos-a.akamaihd.net/abc_xyz_o.jpg'},
  'attachments': [{
    'objectType': 'image',
    'url': 'http://my.link/',
    'displayName': 'my link name',
    'summary': 'my link caption',
    'content': 'my link description',
    'image': {'url': 'https://fbcdn-photos-a.akamaihd.net/abc_xyz_o.jpg'}
  }],
  'to': [{'objectType':'group', 'alias':'@public'}],
  'location': {
    'displayName': 'Lake Merced',
    'id': tag_uri('113785468632283'),
    'url': 'https://www.github.com/113785468632283',
    'latitude': 37.728193717481,
    'longitude': -122.49336423595,
    'position': '+37.728194-122.493364/',
  },
  'tags': [{
      'objectType': 'person',
      'id': tag_uri('234'),
      'url': 'https://www.github.com/234',
      'displayName': 'Friend 1',
  }],
  'replies': {
    'items': [COMMENT_OBJ],
    'totalItems': 1,
  }
}
ISSUE_ACTIVITY = {  # ActivityStreams
  'verb': 'post',
  'published': '2012-03-04T18:20:37+00:00',
  'updated': '2012-03-04T19:08:16+00:00',
  'id': tag_uri('10100176064482163'),
  'fb_id': '212038_10100176064482163',
  'url': 'https://www.github.com/212038/posts/10100176064482163',
  'actor': ISSUE_OBJ['author'],
  'object': ISSUE_OBJ,
  'generator': {
    'displayName': 'GitHub for Android',
    'id': tag_uri('350685531728'),
  },
}


class GitHubTest(testutil.HandlerTest):

  def setUp(self):
    super(GitHubTest, self).setUp()
    self.gh = github.GitHub()
    self.batch = []
    self.batch_responses = []

  def expect_graphql(self, response=None, **kwargs):
    return super(GitHubTest, self).expect_requests_post(
      oauth_github.API_GRAPHQL, response=json.dumps(response), **kwargs)

  def test_user_to_actor_full(self):
    self.assert_equals(ACTOR, self.gh.user_to_actor(USER))

  def test_user_to_actor_minimal(self):
    actor = self.gh.user_to_actor({'id': '123'})
    self.assert_equals(tag_uri('123'), actor['id'])

  def test_user_to_actor_empty(self):
    self.assert_equals({}, self.gh.user_to_actor({}))

  # def test_get_actor(self):
  #   self.expect_urlopen('foo', USER)
  #   self.mox.ReplayAll()
  #   self.assert_equals(ACTOR, self.gh.get_actor('foo'))

  # def test_get_actor_default(self):
  #   self.expect_urlopen('me', USER)
  #   self.mox.ReplayAll()
  #   self.assert_equals(ACTOR, self.gh.get_actor())

  # def test_get_activities_defaults(self):
  #   resp = {'data': [
  #         {'id': '1_2', 'message': 'foo'},
  #         {'id': '3_4', 'message': 'bar'},
  #         ]}
  #   self.expect_urlopen('me/home?offset=0', resp)
  #   self.mox.ReplayAll()

  #   self.assert_equals([
  #       {'id': tag_uri('2'),
  #        'fb_id': '1_2',
  #        'object': {'content': 'foo',
  #                   'id': tag_uri('2'),
  #                   'fb_id': '1_2',
  #                   'objectType': 'note',
  #                   'url': 'https://www.github.com/1/posts/2'},
  #        'url': 'https://www.github.com/1/posts/2',
  #        'verb': 'post'},
  #       {'id': tag_uri('4'),
  #        'fb_id': '3_4',
  #        'object': {'content': 'bar',
  #                   'id': tag_uri('4'),
  #                   'fb_id': '3_4',
  #                   'objectType': 'note',
  #                   'url': 'https://www.github.com/3/posts/4'},
  #        'url': 'https://www.github.com/3/posts/4',
  #        'verb': 'post'}],
  #     self.gh.get_activities())

  # def test_get_activities_self_empty(self):
  #   self.expect_urlopen(API_ME_POSTS, {})
  #   self.expect_urlopen(API_PHOTOS_UPLOADED, {})
  #   self.mox.ReplayAll()
  #   self.assert_equals([], self.gh.get_activities(group_id=source.SELF))

  # def test_get_activities_activity_id_not_found(self):
  #   self.expect_urlopen(API_OBJECT % ('0', '0'), {
  #     'error': {
  #       'message': '(#803) Some of the aliases you requested do not exist: 0',
  #       'type': 'OAuthException',
  #       'code': 803
  #     }
  #   })
  #   self.mox.ReplayAll()
  #   self.assert_equals([], self.gh.get_activities(activity_id='0_0'))

  # def test_get_activities_start_index_and_count(self):
  #   self.expect_urlopen('me/home?offset=3&limit=5', {})
  #   self.mox.ReplayAll()
  #   self.gh.get_activities(start_index=3, count=5)

  # def test_get_activities_start_index_count_zero(self):
  #   self.expect_urlopen('me/home?offset=0', {'data': [POST, FB_NOTE]})
  #   self.mox.ReplayAll()
  #   self.assert_equals([ACTIVITY, FB_NOTE_ACTIVITY],
  #                      self.gh.get_activities(start_index=0, count=0))

  # def test_get_activities_count_past_end(self):
  #   self.expect_urlopen('me/home?offset=0&limit=9', {'data': [POST]})
  #   self.mox.ReplayAll()
  #   self.assert_equals([ACTIVITY], self.gh.get_activities(count=9))

  # def test_get_activities_start_index_past_end(self):
  #   self.expect_urlopen('me/home?offset=0', {'data': [POST]})
  #   self.mox.ReplayAll()
  #   self.assert_equals([ACTIVITY], self.gh.get_activities(offset=9))

  # def test_get_activities_activity_id_with_user_id(self):
  #   self.expect_urlopen(API_OBJECT % ('12', '34'), {'id': '123'})
  #   self.mox.ReplayAll()
  #   obj = self.gh.get_activities(activity_id='34', user_id='12')[0]['object']
  #   self.assertEquals('123', obj['fb_id'])

  # def test_get_activities_fetch_replies(self):
  #   post2 = copy.deepcopy(POST)
  #   post2['id'] = '222'
  #   post3 = copy.deepcopy(POST)
  #   post3['id'] = '333'
  #   self.expect_urlopen('me/home?offset=0',
  #                       {'data': [POST, post2, post3]})
  #   self.expect_urlopen(API_COMMENTS_ALL % '212038_10100176064482163,222,333',
  #     {'222': {'data': [{'id': '777', 'message': 'foo'},
  #                       {'id': '888', 'message': 'bar'}]},
  #      '333': {'data': [{'id': '999', 'message': 'baz'},
  #                       {'id': COMMENTS[0]['id'], 'message': 'omitted!'}]},
  #     })
  #   self.mox.ReplayAll()

  #   activities = self.gh.get_activities(fetch_replies=True)
  #   base_ids = ['547822715231468_6796480', '124561947600007_672819']
  #   self.assert_equals([base_ids, base_ids + ['777', '888'], base_ids + ['999']],
  #                      [[c['fb_id'] for c in a['object']['replies']['items']]
  #                       for a in activities])

  # def test_get_activities_search_not_implemented(self):
  #   with self.assertRaises(NotImplementedError):
  #     self.gh.get_activities(search_query='foo')

  # def test_get_comment(self):
  #   self.expect_urlopen(API_COMMENT % '123_456', COMMENTS[0])
  #   self.mox.ReplayAll()
  #   self.assert_equals(COMMENT_OBJS[0], self.gh.get_comment('123_456'))

  # def test_issue_to_activity_full(self):
  #   self.assert_equals(ACTIVITY, self.gh.issue_to_activity(ISSUE))

  # def test_issue_to_activity_minimal(self):
  #   # just test that we don't crash
  #   self.gh.issue_to_activity({'id': '123_456', 'message': 'asdf'})

  # def test_issue_to_activity_empty(self):
  #   # just test that we don't crash
  #   self.gh.issue_to_activity({})

  # def test_issue_to_object_full(self):
  #   self.assert_equals(ISSUE_OBJ, self.gh.issue_to_object(ISSUE))

  # def test_issue_to_object_minimal(self):
  #   # just test that we don't crash
  #   self.gh.issue_to_object({'id': '123_456', 'message': 'asdf'})

  # def test_issue_to_object_empty(self):
  #   self.assert_equals({}, self.gh.issue_to_object({}))

  # def test_comment_to_object_full(self):
  #   for cmt, obj in zip(COMMENTS, COMMENT_OBJS):
  #     self.assert_equals(obj, self.gh.comment_to_object(cmt))

  # def test_comment_to_object_minimal(self):
  #   # just test that we don't crash
  #   self.gh.comment_to_object({'id': '123_456_789', 'message': 'asdf'})

  # def test_comment_to_object_empty(self):
  #   self.assert_equals({}, self.gh.comment_to_object({}))

  # def test_create_issue(self):
  #   self.expect_urlopen(API_PUBLISH_POST, {'id': '123_456'}, data=urllib.urlencode({
  #       'message': 'my msg',
  #       'tags': '234,345,456',
  #     }))
  #   self.mox.ReplayAll()

  #   obj = copy.deepcopy(POST_OBJ)
  #   del obj['image']
  #   obj.update({
  #       'objectType': 'note',
  #       'content': 'my msg',
  #       })
  #   self.assert_equals({
  #     'id': '123_456',
  #     'url': 'https://www.github.com/123/posts/456',
  #     'type': 'post',
  #   }, self.gh.create(obj).content)

  #   preview = self.gh.preview_create(obj)
  #   self.assertEquals('<span class="verb">post</span>:', preview.description)
  #   self.assertEquals('my msg<br /><br /><em>with <a href="https://www.github.com/234">Friend 1</a>, <a href="https://www.github.com/345">Friend 2</a>, <a href="https://www.github.com/456">Friend 3</a></em>', preview.content)

  def test_create_comment(self):
    self.expect_graphql(json={
      'query': github.GRAPHQL_ISSUE_OR_PR % {
        'owner': 'foo',
        'repo': 'bar',
        'number': 123,
      },
    }, response={'data': {
      'repository': {
        'issueOrPullRequest': ISSUE,
      },
    }})
    self.expect_graphql(json={
      'mutation': github.GRAPHQL_ADD_COMMENT % {
        'subject_id': ISSUE['id'],
        'body': 'i have something to say here',
      },
    }, response={'data': {
      'addComment': {
        'commentEdge': {
          'node': {
            'id': '456',
            'url': 'https://github.com/foo/bar/pull/123#comment-456',
          },
        },
      },
    }})
    self.mox.ReplayAll()

    result = self.gh.create(COMMENT_OBJ)
    self.assert_equals({
      'id': '456',
      'url': 'https://github.com/foo/bar/pull/123#comment-456',
    }, result.content, result)

  # def test_preview_comment(self):
  #   preview = self.gh.preview_create(COMMENT_OBJ)
  #   self.assertEquals('my cmt', preview.content)
  #   self.assertIn('<span class="verb">comment</span> on <a href="https://github.com/foo/bar/123">foo/bar#123</a>:', preview.description)

  # def test_create_unsupported_type(self):
  #   for fn in self.gh.create, self.gh.preview_create:
  #     result = fn({'objectType': 'activity', 'verb': 'share'})
  #     self.assertTrue(result.abort)
  #     self.assertIn('Cannot publish shares', result.error_plain)
  #     self.assertIn('Cannot publish', result.error_html)

  # def test_create_comment_without_in_reply_to(self):
  #   obj = copy.deepcopy(COMMENT_OBJS[0])
  #   obj['inReplyTo'] = [{'url': 'http://foo.com/bar'}]

  #   for fn in (self.gh.preview_create, self.gh.create):
  #     preview = fn(obj)
  #     self.assertTrue(preview.abort)
  #     self.assertIn('Could not find a GitHub status to reply to', preview.error_plain)
  #     self.assertIn('Could not find a GitHub status to', preview.error_html)
