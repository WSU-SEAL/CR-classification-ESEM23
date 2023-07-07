package yunogum.MetricCalculator;

import java.util.List;
import java.util.Map;

import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.TreeClassifier;

import yunogum.PythonFileData;

public abstract class MetricCalculator {
    public abstract void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData);
    public abstract void putHeader(List<String> headers);
}
