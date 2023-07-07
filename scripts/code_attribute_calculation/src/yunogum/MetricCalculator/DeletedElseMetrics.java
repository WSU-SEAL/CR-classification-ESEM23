package yunogum.MetricCalculator;

import java.util.List;
import java.util.Map;

import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.TreeClassifier;

import yunogum.PythonFileData;

public class DeletedElseMetrics extends ElseMetrics{

    public void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData) {
        int elseDeleted = countElse(classifier.getDeletedSrcs(), fileData, true);

        metrics.put("elseDeleted", elseDeleted);
    }



    public void putHeader(List<String> headers){
        headers.add("elseDeleted");
    }


}