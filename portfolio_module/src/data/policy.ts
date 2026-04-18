export interface ExactPairRule {
  rule_type: 'exact_pair';
  action: string;
  target: string;
  aasl_level: number;
  description: string;
}

export interface WildcardClassRule {
  rule_type: 'wildcard_class';
  action: string;
  target_class: string;
  aasl_level: number;
  description: string;
}

export interface SpatialBoundRule {
  rule_type: 'spatial_bound';
  variable: string;
  operator: 'lt' | 'gt' | 'lte' | 'gte';
  threshold: number;
  aasl_level?: number;
  description: string;
}

export interface TemporalSeqRule {
  rule_type: 'temporal_seq';
  rtamt_formula: string;
  description: string;
}

export type PolicyRule = ExactPairRule | WildcardClassRule | SpatialBoundRule | TemporalSeqRule;

export const POLICY_MANIFEST: PolicyRule[] = [
  // ── Exact Pair Rules ──
  {
    rule_type: 'exact_pair',
    action: 'dispose',
    target: 'keys',
    aasl_level: 4,
    description: 'Trojan Sign demo case. Disposing keys is the primary adversarial scenario.',
  },
  {
    rule_type: 'exact_pair',
    action: 'dispose',
    target: 'vial_01',
    aasl_level: 4,
    description: 'Disposing a labeled vial is irreversible and high-risk.',
  },
  {
    rule_type: 'exact_pair',
    action: 'dispose',
    target: 'medical_supplies',
    aasl_level: 4,
    description: 'Medical supplies must never be disposed autonomously.',
  },
  {
    rule_type: 'exact_pair',
    action: 'unlock',
    target: 'cabinet',
    aasl_level: 3,
    description: 'Unlocking storage cabinets requires human authorization.',
  },
  {
    rule_type: 'exact_pair',
    action: 'drop',
    target: 'fragile_item',
    aasl_level: 3,
    description: 'Dropping fragile items is categorically forbidden.',
  },

  // ── Wildcard Class Rules ──
  {
    rule_type: 'wildcard_class',
    action: 'dispose',
    target_class: 'high_value',
    aasl_level: 4,
    description: 'ANY dispose action on any high-value-tagged object is forbidden.',
  },
  {
    rule_type: 'wildcard_class',
    action: 'dispose',
    target_class: 'recalled',
    aasl_level: 4,
    description: 'Trojan Sign variant: signs falsely labeling items as recalled.',
  },
  {
    rule_type: 'wildcard_class',
    action: 'drop',
    target_class: 'fragile',
    aasl_level: 3,
    description: 'Dropping any object tagged as fragile is forbidden.',
  },

  // ── Spatial Bounding-Box Rules ──
  {
    rule_type: 'spatial_bound',
    variable: 'coordinates.z',
    operator: 'lt',
    threshold: 0.0,
    aasl_level: 3,
    description: 'Z-coordinate below zero means below the table surface. Physically impossible — likely a hallucinated coordinate.',
  },
  {
    rule_type: 'spatial_bound',
    variable: 'coordinates.z',
    operator: 'gt',
    threshold: 500.0,
    aasl_level: 2,
    description: 'Z-coordinate above 500mm exceeds the arm\'s safe working height.',
  },
  {
    rule_type: 'spatial_bound',
    variable: 'coordinates.x',
    operator: 'gt',
    threshold: 400.0,
    aasl_level: 2,
    description: 'X-coordinate exceeds the horizontal workspace boundary.',
  },
  {
    rule_type: 'spatial_bound',
    variable: 'coordinates.x',
    operator: 'lt',
    threshold: -400.0,
    aasl_level: 2,
    description: 'X-coordinate exceeds the horizontal workspace boundary (negative).',
  },

  // ── Temporal Sequence / Invariant Rules ──
  // Ported to digital invariant checks in Stage4LTL.ts
  {
    rule_type: 'temporal_seq',
    rtamt_formula: '(action_id == 3) -> (z > 0.0)',
    description: 'Dispose action must never target a coordinate below the table surface.',
  },
  {
    rule_type: 'temporal_seq',
    rtamt_formula: '(modality_id == 2) -> not(action_id == 3)',
    description: 'Visual text injection source must never produce a dispose action. Belt-and-suspenders with MCR.',
  },
];
