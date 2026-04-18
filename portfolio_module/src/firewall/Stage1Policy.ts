import { IntentPacket, VetoPacket, AASLConfig } from './types';
import { POLICY_MANIFEST, ExactPairRule, WildcardClassRule } from '../data/policy';

export class Stage1Policy {
  private exactRules: ExactPairRule[] = [];
  private wildcardRules: WildcardClassRule[] = [];

  constructor() {
    this.exactRules = POLICY_MANIFEST.filter((r): r is ExactPairRule => r.rule_type === 'exact_pair');
    this.wildcardRules = POLICY_MANIFEST.filter((r): r is WildcardClassRule => r.rule_type === 'wildcard_class');
  }

  public validate(intent: IntentPacket): VetoPacket | null {
    const action = intent.action.toLowerCase();
    const target = intent.target.toLowerCase();

    // 1. Exact Match
    for (const rule of this.exactRules) {
      if (rule.action === action && rule.target === target) {
        return {
          request_id: intent.request_id,
          decision: 'VETO',
          reason: `Forbidden action/target pair: '${action}' on '${target}' (match: exact).`,
          source: 'RadixTree', // Kept name for UI compatibility
          latency_ms: 0,
          hitl_override_token: null,
        };
      }
    }

    // 2. Wildcard Match
    for (const rule of this.wildcardRules) {
      if (rule.action === action && target.includes(rule.target_class)) {
        return {
          request_id: intent.request_id,
          decision: 'VETO',
          reason: `Forbidden action/target pair: '${action}' on '${target}' (match: wildcard).`,
          source: 'RadixTree',
          latency_ms: 0,
          hitl_override_token: null,
        };
      }
    }

    return null;
  }
}
