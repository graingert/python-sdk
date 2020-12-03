# Copyright 2020, Optimizely
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json

import mock

from optimizely.decision.decide_option import DecideOption
from optimizely.event.event_factory import EventFactory
from optimizely.helpers import enums
from . import base
from optimizely import logger, optimizely, decision_service
from optimizely.user_context import UserContext


class UserContextTests(base.BaseTest):
    def setUp(self):
        base.BaseTest.setUp(self, 'config_dict_with_multiple_experiments')
        self.logger = logger.NoOpLogger()

    def test_user_context(self):
        """
        tests user context creating and attributes
        """
        uc = UserContext(self.optimizely, "test_user")
        self.assertEqual(uc.user_attributes, {}, "should have created default empty")
        self.assertEqual(uc.user_id, "test_user", "should have same user id")
        uc.set_attribute("key", "value")
        self.assertEqual(uc.user_attributes["key"], "value", "should have added attribute")
        uc.set_attribute("key", "value2")
        self.assertEqual(uc.user_attributes["key"], "value2", "should have new attribute")

    def test_decide_feature_test(self):
        opt_obj = optimizely.Optimizely(json.dumps(self.config_dict_with_features))
        project_config = opt_obj.config_manager.get_config()

        mock_experiment = project_config.get_experiment_from_key('test_experiment')
        mock_variation = project_config.get_variation_from_id('test_experiment', '111129')
        with mock.patch(
            'optimizely.decision_service.DecisionService.get_variation_for_feature',
            return_value=decision_service.Decision(mock_experiment, mock_variation, enums.DecisionSources.FEATURE_TEST),
        ):
            user_context = opt_obj.create_user_context('test_user')
            decision = user_context.decide('test_feature_in_experiment', [DecideOption.DISABLE_DECISION_EVENT])
            self.assertTrue(decision.enabled, "decision should be enabled")

    def test_decide_rollout(self):
        """ Test that the feature is enabled for the user if bucketed into variation of a rollout.
    Also confirm that no impression event is processed. """

        opt_obj = optimizely.Optimizely(json.dumps(self.config_dict_with_features))

        user_context = opt_obj.create_user_context('test_user')
        decision = opt_obj.decide(user_context, 'test_feature_in_rollout')
        self.assertFalse(decision.enabled)
        self.assertEqual(decision.flag_key, 'test_feature_in_rollout')

    def test_decide_for_keys(self):
        """ Test that the feature is enabled for the user if bucketed into variation of a rollout.
    Also confirm that no impression event is processed. """

        opt_obj = optimizely.Optimizely(json.dumps(self.config_dict_with_features))

        user_context = opt_obj.create_user_context('test_user')
        decisions = opt_obj.decide_for_keys(user_context, ['test_feature_in_rollout', 'test_feature_in_experiment'])
        self.assertTrue(len(decisions) == 2)

        self.assertFalse(decisions['test_feature_in_rollout'].enabled)
        self.assertEqual(decisions['test_feature_in_rollout'].flag_key, 'test_feature_in_rollout')

        self.assertFalse(decisions['test_feature_in_experiment'].enabled)
        self.assertEqual(decisions['test_feature_in_experiment'].flag_key, 'test_feature_in_experiment')

    def test_decide_all(self):
        """ Test that the feature is enabled for the user if bucketed into variation of a rollout.
    Also confirm that no impression event is processed. """

        opt_obj = optimizely.Optimizely(json.dumps(self.config_dict_with_features))

        user_context = opt_obj.create_user_context('test_user')
        decisions = opt_obj.decide_all(user_context)
        self.assertTrue(len(decisions) == 4)

        self.assertFalse(decisions['test_feature_in_rollout'].enabled)
        self.assertEqual(decisions['test_feature_in_rollout'].flag_key, 'test_feature_in_rollout')

        self.assertFalse(decisions['test_feature_in_experiment'].enabled)
        self.assertEqual(decisions['test_feature_in_experiment'].flag_key, 'test_feature_in_experiment')

        self.assertFalse(decisions['test_feature_in_group'].enabled)
        self.assertEqual(decisions['test_feature_in_group'].flag_key, 'test_feature_in_group')

        self.assertFalse(decisions['test_feature_in_experiment_and_rollout'].enabled)
        self.assertEqual(decisions['test_feature_in_experiment_and_rollout'].flag_key,
                         'test_feature_in_experiment_and_rollout')

    def test_decide_all_enabled_only(self):
        """ Test that the feature is enabled for the user if bucketed into variation of a rollout.
    Also confirm that no impression event is processed. """

        opt_obj = optimizely.Optimizely(json.dumps(self.config_dict_with_features))

        user_context = opt_obj.create_user_context('test_user')
        decisions = opt_obj.decide_all(user_context, [DecideOption.ENABLED_FLAGS_ONLY])
        self.assertTrue(len(decisions) == 0)

    def test_track(self):
        """ Test that the feature is enabled for the user if bucketed into variation of a rollout.
    Also confirm that no impression event is processed. """

        opt_obj = optimizely.Optimizely(json.dumps(self.config_dict_with_features))

        with mock.patch('time.time', return_value=42), mock.patch(
            'uuid.uuid4', return_value='a68cf1ad-0393-4e18-af87-efe8f01a7c9c'
        ), mock.patch('optimizely.event.event_processor.ForwardingEventProcessor.process') as mock_process:
            user_context = opt_obj.create_user_context('test_user')
            user_context.track_event('test_event')

        log_event = EventFactory.create_log_event(mock_process.call_args[0][0], opt_obj.logger)
        self.assertEqual(log_event.params['visitors'][0]['visitor_id'], 'test_user')
        self.assertEqual(log_event.params['visitors'][0]['snapshots'][0]['events'][0]['timestamp'], 42000)
        self.assertEqual(log_event.params['visitors'][0]['snapshots'][0]['events'][0]['uuid'],
                         'a68cf1ad-0393-4e18-af87-efe8f01a7c9c')
        self.assertEqual(log_event.params['visitors'][0]['snapshots'][0]['events'][0]['key'], 'test_event')