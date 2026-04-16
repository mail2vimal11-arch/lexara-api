"""
Advanced training data — Part 4: Legal drafting style, rewrite pairs,
chain-of-thought clause analysis, and deontic logic training.
"""

# ── Pillar 1: Active Voice & Nominalization Rewrites ─────────
ACTIVE_VOICE_TRAINING = [
    {
        "instruction": "Rewrite this clause using active voice. Eliminate passive constructions and nominalizations.",
        "input": "Delivery of the goods shall be made by the Vendor within 30 days of the issuance of a purchase order by the Purchaser.",
        "output": "The Vendor must deliver the goods within 30 days after the Purchaser issues a purchase order."
    },
    {
        "instruction": "Rewrite this clause using active voice. Eliminate passive constructions and nominalizations.",
        "input": "It is required that consideration be given by the parties to the termination provisions prior to the execution of this Agreement.",
        "output": "The parties must consider the termination provisions before executing this Agreement."
    },
    {
        "instruction": "Rewrite this clause using active voice. Eliminate passive constructions and nominalizations.",
        "input": "Payment of undisputed invoices shall be made by Canada within thirty calendar days of receipt of a properly rendered invoice submitted by the Contractor.",
        "output": "Canada must pay undisputed invoices within thirty calendar days after receiving a properly rendered invoice from the Contractor."
    },
    {
        "instruction": "Rewrite this clause using active voice. Eliminate passive constructions and nominalizations.",
        "input": "The determination of whether a Force Majeure event has occurred shall be made by Canada in its sole discretion upon the submission of evidence by the Contractor.",
        "output": "Canada will determine whether a Force Majeure event has occurred, in its sole discretion, after the Contractor submits evidence."
    },
    {
        "instruction": "Rewrite this clause using active voice. Eliminate passive constructions and nominalizations.",
        "input": "Upon the occurrence of an event of default, acceleration of all outstanding amounts may be declared by the Lender and the provision of further advances shall be discontinued.",
        "output": "If the Borrower defaults, the Lender may declare all outstanding amounts immediately due and must stop providing further advances."
    },
    {
        "instruction": "Rewrite this clause using active voice. Eliminate passive constructions and nominalizations.",
        "input": "A review of the deliverables shall be conducted by the Technical Authority and a notification of acceptance or rejection shall be provided to the Contractor within fifteen business days.",
        "output": "The Technical Authority must review the deliverables and notify the Contractor of acceptance or rejection within fifteen business days."
    },
    {
        "instruction": "Rewrite this clause using active voice. Eliminate passive constructions and nominalizations.",
        "input": "Compliance with all applicable federal and provincial privacy legislation is required to be maintained by the Contractor throughout the performance of the Contract.",
        "output": "The Contractor must comply with all applicable federal and provincial privacy legislation throughout the Contract."
    },
    {
        "instruction": "Rewrite this clause using active voice. Eliminate passive constructions and nominalizations.",
        "input": "An assessment of the environmental impact of the proposed development is to be carried out by the proponent and submission of the results to the Authority is required prior to the commencement of construction activities.",
        "output": "The proponent must assess the environmental impact of the proposed development and submit the results to the Authority before starting construction."
    },
]

# ── Pillar 2: Deontic Logic (Must/May/Shall) ────────────────
DEONTIC_LOGIC_TRAINING = [
    {
        "instruction": "Correct the deontic modals in this clause. Use 'must' for obligations, 'may' for discretion, and avoid ambiguous use of 'shall'.",
        "input": "The Contractor shall deliver the reports. Canada shall have the right to reject non-conforming work. The parties shall negotiate in good faith.",
        "output": "The Contractor must deliver the reports. Canada may reject non-conforming work. The parties must negotiate in good faith."
    },
    {
        "instruction": "Correct the deontic modals in this clause. Use 'must' for obligations, 'may' for discretion, and avoid ambiguous use of 'shall'.",
        "input": "The Vendor shall provide notice. The Purchaser shall, at its option, terminate the Agreement. Disputes shall be resolved by arbitration.",
        "output": "The Vendor must provide notice. The Purchaser may, at its option, terminate the Agreement. The parties must resolve disputes by arbitration."
    },
    {
        "instruction": "Correct the deontic modals in this clause. Use 'must' for obligations, 'may' for discretion, and avoid ambiguous use of 'shall'.",
        "input": "The Employee shall not disclose confidential information. The Employer shall have the right to audit. Termination shall occur upon 30 days notice.",
        "output": "The Employee must not disclose confidential information. The Employer may audit at any time. Either party may terminate by giving 30 days notice."
    },
    {
        "instruction": "Analyze the deontic logic in this clause. Identify each obligation (must), permission (may), and prohibition (must not). Return JSON.",
        "input": "The Contractor shall maintain insurance coverage. Canada may request certificates at any time. The Contractor shall not assign without consent. Either party shall have the right to terminate for convenience.",
        "output": '{"analysis": [{"original": "The Contractor shall maintain insurance coverage", "modal": "shall", "corrected_modal": "must", "type": "obligation", "corrected": "The Contractor must maintain insurance coverage"}, {"original": "Canada may request certificates at any time", "modal": "may", "corrected_modal": "may", "type": "permission", "corrected": "Canada may request certificates at any time"}, {"original": "The Contractor shall not assign without consent", "modal": "shall not", "corrected_modal": "must not", "type": "prohibition", "corrected": "The Contractor must not assign without consent"}, {"original": "Either party shall have the right to terminate for convenience", "modal": "shall have the right", "corrected_modal": "may", "type": "permission", "corrected": "Either party may terminate for convenience"}]}'
    },
]

# ── Pillar 3: Singular Rule ─────────────────────────────────
SINGULAR_RULE_TRAINING = [
    {
        "instruction": "Rewrite this clause using the singular form to eliminate ambiguity. Use 'The Contractor' not 'Contractors', 'The Employee' not 'Employees'.",
        "input": "Contractors must ensure that their employees comply with all site safety regulations. Bidders shall submit proposals in triplicate.",
        "output": "The Contractor must ensure that each employee complies with all site safety regulations. The Bidder must submit a proposal in triplicate."
    },
    {
        "instruction": "Rewrite this clause using the singular form to eliminate ambiguity.",
        "input": "Vendors who fail to deliver on time will be subject to liquidated damages. Subcontractors are required to hold valid insurance.",
        "output": "A Vendor who fails to deliver on time is subject to liquidated damages. Each Subcontractor must hold valid insurance."
    },
    {
        "instruction": "Rewrite this clause using the singular form to eliminate ambiguity.",
        "input": "Shareholders holding more than 10% of shares must disclose their holdings. Directors are required to act in good faith.",
        "output": "A Shareholder holding more than 10% of shares must disclose the holding. Each Director must act in good faith."
    },
]

# ── Pillar 4: Consistency (One Word Rule) ────────────────────
CONSISTENCY_TRAINING = [
    {
        "instruction": "Identify terminology inconsistencies in this contract excerpt. Flag where synonyms are used for the same concept, which creates ambiguity.",
        "input": "Section 1: The Supplier shall deliver the Equipment by June 30. Section 5: The Vendor guarantees that all Devices will function as specified. Section 8: The Provider warrants that the Products meet the acceptance criteria. Section 12: Upon delivery of the Goods, the Purchaser shall inspect the items within 10 days.",
        "output": '{"inconsistencies": [{"concept": "The party providing goods", "terms_used": ["Supplier", "Vendor", "Provider"], "recommendation": "Use \'Supplier\' consistently throughout (defined term in Section 1)"}, {"concept": "The items being provided", "terms_used": ["Equipment", "Devices", "Products", "Goods", "items"], "recommendation": "Use \'Equipment\' consistently (defined term in Section 1) or define \'Deliverables\' as a catch-all"}, {"concept": "Quality assurance", "terms_used": ["guarantees", "warrants"], "recommendation": "Use \'warrants\' consistently — \'guarantee\' has a separate legal meaning (suretyship)"}], "corrected_excerpt": "Section 1: The Supplier must deliver the Equipment by June 30. Section 5: The Supplier warrants that the Equipment will function as specified. Section 8: The Supplier warrants that the Equipment meets the acceptance criteria. Section 12: Upon delivery of the Equipment, the Purchaser must inspect the Equipment within 10 days."}'
    },
    {
        "instruction": "Identify terminology inconsistencies in this contract excerpt.",
        "input": "The Agreement commences on the Start Date. The Contract shall remain in force until the End Date. This Arrangement may be terminated by either party. Upon expiry of this Deal, all obligations cease.",
        "output": '{"inconsistencies": [{"concept": "This contract", "terms_used": ["Agreement", "Contract", "Arrangement", "Deal"], "recommendation": "Use \'Agreement\' consistently (first defined reference). \'Deal\' is informal and inappropriate for legal drafting."}, {"concept": "Start of term", "terms_used": ["commences", "Start Date"], "recommendation": "Define \'Effective Date\' and use it consistently."}, {"concept": "End of term", "terms_used": ["End Date", "terminated", "expiry"], "recommendation": "Distinguish: \'Expiration Date\' for natural end, \'termination\' for early end. Never use both for the same concept."}]}'
    },
]

# ── Chain-of-Thought Clause Analysis ─────────────────────────
COT_CLAUSE_ANALYSIS = [
    {
        "instruction": "Analyze this clause step-by-step. Step 1: Identify the Actor. Step 2: Identify the Action. Step 3: Identify the Deadline. Step 4: Identify the Consequence. Step 5: Rate the risk.",
        "input": "The Contractor shall use reasonable efforts to deliver the final report within a reasonable time after receiving Canada's comments, failing which Canada may, at its discretion, withhold payment.",
        "output": '{"step_1_actor": "The Contractor", "step_2_action": "Deliver the final report after receiving Canada\'s comments", "step_3_deadline": "AMBIGUOUS — \'within a reasonable time\' is not a specific deadline. This should be \'within 10 business days\' or similar.", "step_4_consequence": "Canada may withhold payment (discretionary, not automatic)", "step_5_risk": {"level": "High", "issues": ["\'Reasonable efforts\' is a weak standard — should be \'must deliver\'", "\'Reasonable time\' is undefined — creates dispute risk", "Consequence is discretionary (\'may\') not automatic — weak enforcement"], "improved": "The Contractor must deliver the final report within 10 business days after receiving Canada\'s comments. If the Contractor fails to deliver within this period, Canada may withhold payment until delivery."}}'
    },
    {
        "instruction": "Analyze this clause step-by-step. Step 1: Identify the Actor. Step 2: Identify the Action. Step 3: Identify the Deadline. Step 4: Identify the Consequence. Step 5: Rate the risk.",
        "input": "Upon becoming aware of a data breach, the Processor shall notify the Controller as soon as practicable and in any event within 72 hours, providing details of the nature of the breach, the categories and approximate number of data subjects affected, and the measures taken or proposed to address the breach.",
        "output": '{"step_1_actor": "The Processor", "step_2_action": "Notify the Controller of a data breach with specified details (nature, affected subjects, remedial measures)", "step_3_deadline": "72 hours from becoming aware — CLEAR and specific", "step_4_consequence": "Not stated — should add: \'Failure to notify within 72 hours constitutes a material breach\'", "step_5_risk": {"level": "Low-Medium", "issues": ["Deadline is clear (72 hours)", "Required content is specific", "Missing: consequence for late notification", "Missing: who determines \'becoming aware\' — add \'knew or ought to have known\'"], "improved": "When the Processor knows or ought to know of a data breach, the Processor must notify the Controller within 72 hours, providing: (a) the nature of the breach; (b) the categories and approximate number of affected data subjects; (c) the measures taken or proposed to address the breach. Failure to notify within 72 hours constitutes a material breach of this Agreement."}}'
    },
    {
        "instruction": "Analyze this clause step-by-step. Step 1: Identify the Actor. Step 2: Identify the Action. Step 3: Identify the Deadline. Step 4: Identify the Consequence. Step 5: Rate the risk.",
        "input": "The parties hereto agree that in the event of a dispute arising hereunder, they shall endeavour to resolve same through good faith negotiations for a period not exceeding 30 days, and failing resolution, the matter may be referred to arbitration.",
        "output": '{"step_1_actor": "Both parties (\'parties hereto\')", "step_2_action": "Negotiate in good faith to resolve disputes, then optionally arbitrate", "step_3_deadline": "30 days for negotiation — CLEAR", "step_4_consequence": "May refer to arbitration — WEAK (permissive, not mandatory)", "step_5_risk": {"level": "Medium", "issues": ["\'Endeavour\' is weaker than \'must\' — creates no real obligation to negotiate", "\'May be referred\' makes arbitration optional — either party could go to court instead", "\'Hereto\' and \'hereunder\' and \'same\' are archaic legalese", "No specification of arbitration rules, seat, or number of arbitrators"], "improved": "If a dispute arises under this Agreement, the parties must first attempt to resolve it through good-faith negotiation for 30 days. If the dispute is not resolved within 30 days, either party must refer it to binding arbitration under the Arbitration Act, 1991, SO 1991, c 17, conducted by a single arbitrator in Toronto, Ontario."}}'
    },
    {
        "instruction": "Analyze this clause step-by-step. Step 1: Identify the Actor. Step 2: Identify the Action. Step 3: Identify the Deadline. Step 4: Identify the Consequence. Step 5: Rate the risk.",
        "input": "The Supplier shall indemnify the Buyer against any and all losses howsoever arising from the Supplier's performance of this Contract.",
        "output": '{"step_1_actor": "The Supplier", "step_2_action": "Indemnify the Buyer against all losses from Supplier\'s performance", "step_3_deadline": "None stated — should specify notice period for claims", "step_4_consequence": "Full indemnification — VERY BROAD", "step_5_risk": {"level": "High (for Supplier) / Low (for Buyer)", "issues": ["\'Any and all losses howsoever arising\' is unlimited in scope — extremely broad", "No cap on indemnification amount", "No requirement for Buyer to mitigate losses", "No notice or cooperation requirements", "No exclusion for Buyer\'s own negligence or misuse", "\'Howsoever arising\' could include consequential and indirect losses"], "improved": "The Supplier must indemnify the Buyer against direct losses arising from the Supplier\'s negligence or breach of this Contract, subject to: (a) the Buyer notifying the Supplier in writing within 30 days of becoming aware of a claim; (b) the Buyer providing reasonable cooperation; (c) the Supplier having sole control of the defence; (d) aggregate indemnification not exceeding 2x the annual Contract value; (e) claims being brought within 24 months of the event giving rise to the claim."}}'
    },
]

# ── All Part 4 training data combined ────────────────────────
ALL_DRAFTING_STYLE_TRAINING = (
    ACTIVE_VOICE_TRAINING
    + DEONTIC_LOGIC_TRAINING
    + SINGULAR_RULE_TRAINING
    + CONSISTENCY_TRAINING
    + COT_CLAUSE_ANALYSIS
)
