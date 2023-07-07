package yunogum.MetricCalculator;

import java.util.List;
import java.util.Map;

import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.TreeClassifier;

import yunogum.PythonFileData;

public class InsertedElseMetrics extends ElseMetrics{

    public void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData) {

    }



    public void putHeader(List<String> headers){
        headers.add("elseInserted");
    }


    public void getElseMetrics(Diff results, TreeClassifier classifier, Map<String, Integer> metrics, PythonFileData fileData) {
        int elseInserted = countElse(classifier.getInsertedDsts(), fileData, false);
        metrics.put("elseInserted", elseInserted);
    }

}