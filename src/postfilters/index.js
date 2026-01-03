/**
 * Postfilter Registry for MirrorGate
 */

const postfilters = {
    /**
     * forbid_prescriptive_language: Blocks authoritative "you should" patterns.
     */
    forbid_prescriptive_language: async (output) => {
        const prescriptivePatterns = [
            /you should/i,
            /you must/i,
            /the best option is/i,
            /do X/i,
            /I recommend/i
        ];

        if (prescriptivePatterns.some(regex => regex.test(output))) {
            return {
                outcome: 'rewritten',
                output: `⟡ [Policy Injection] One reflection on this is: ${output.replace(/you should|you must|I recommend/gi, "it's possible to consider")}`
            };
        }
        return { outcome: 'allowed', output };
    },

    /**
     * enforce_uncertainty: Ensures markers of epistemic humility.
     */
    enforce_uncertainty: async (output) => {
        const uncertaintyMarkers = ["perhaps", "possible", "unsure", "reflection", "consider", "⟡"];
        if (!uncertaintyMarkers.some(marker => output.toLowerCase().includes(marker))) {
            return {
                outcome: 'rewritten',
                output: `⟡ Perhaps one way to view this is: ${output}`
            };
        }
        return { outcome: 'allowed', output };
    }
};

async function run(output, profile) {
    let currentOutput = output;
    let finalOutcome = 'allowed';

    for (const filter of Object.values(postfilters)) {
        const result = await filter(currentOutput);
        if (result.outcome === 'refused') return result;
        if (result.outcome === 'rewritten') {
            currentOutput = result.output;
            finalOutcome = 'rewritten';
        }
    }

    return { outcome: finalOutcome, output: currentOutput };
}

module.exports = { run };
