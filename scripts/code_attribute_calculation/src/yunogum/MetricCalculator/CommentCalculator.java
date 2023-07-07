package yunogum.MetricCalculator;

import java.util.List;
import java.util.Map;

import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.tree.Tree;

import yunogum.PythonFileData;

public class CommentCalculator extends MetricCalculator{
    public void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData) {

    }



    public void putHeader(List<String> headers){
        headers.add("anyDeleted");
    }
}