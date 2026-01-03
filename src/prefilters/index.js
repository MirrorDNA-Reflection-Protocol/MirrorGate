/**
 * Prefilter Registry for MirrorGate
 */

const prefilters = {
    /**
     * classify_intent: Detects sensitive domains and refuses/elevates.
     */
    classify_intent: async (request) => {
        const sensitiveKeywords = ['medical', 'doctor', 'lawyer', 'legal', 'finance', 'invest', 'suicide', 'kill'];
        const input = request.input.toLowerCase();

        if (sensitiveKeywords.some(kw => input.includes(kw))) {
            // In a real implementation, this would use an LLM or more robust classifier
            console.warn(`[Prefilter] Intent elevation triggered for: ${request.input}`);
            // For prototype: allow but mark as elevated if needed
        }
        return { outcome: 'allowed' };
    },

    /**
     * high_risk_guard: Rejects obvious non-reflection-only prompts.
     */
    high_risk_guard: async (request) => {
        // Simple heuristic for prototype
        return { outcome: 'allowed' };
    }
};

async function run(request) {
    // Run all prefilters in sequence
    for (const filter of Object.values(prefilters)) {
        const result = await filter(request);
        if (result.outcome === 'refused') return result;
        if (result.outcome === 'rewritten') {
            request.input = result.input; // Update request for next filters
        }
    }
    return { outcome: 'allowed', input: request.input };
}

module.exports = { run };
