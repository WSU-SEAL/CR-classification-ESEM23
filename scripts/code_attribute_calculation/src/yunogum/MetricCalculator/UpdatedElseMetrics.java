package yunogum.MetricCalculator;

import java.util.List;
import java.util.Map;

import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.TreeClassifier;

import yunogum.PythonFileData;

public class UpdatedElseMetrics extends ElseMetrics{

    public void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData) {
        int elseUpdated = countElse(classifier.getUpdatedSrcs(), fileData, true);

        metrics.put("elseUpdated", elseUpdated);
    }

    public void putHeader(List<String> headers){
        headers.add("elseUpdated");
    }
}