package yunogum.MetricCalculator;

import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Dictionary;
import java.util.Hashtable;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.List;

import org.hamcrest.core.IsInstanceOf;

import com.github.gumtreediff.*;
import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.EditScript;
import com.github.gumtreediff.actions.EditScriptGenerator;
import com.github.gumtreediff.actions.SimplifiedChawatheScriptGenerator;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.actions.model.Action;
import com.github.gumtreediff.client.Client;
import com.github.gumtreediff.client.Clients;
import com.github.gumtreediff.client.Option;
import com.github.gumtreediff.client.Run;
import com.github.gumtreediff.client.Run.Options;
import com.github.gumtreediff.gen.Registry;
import com.github.gumtreediff.gen.TreeGenerators;
import com.github.gumtreediff.matchers.Mapping;
import com.github.gumtreediff.matchers.MappingStore;
import com.github.gumtreediff.matchers.Matcher;
import com.github.gumtreediff.matchers.Matchers;
import com.github.gumtreediff.tree.DefaultTree;
import com.github.gumtreediff.tree.Tree;

import yunogum.MetricRunner;
import yunogum.PythonFileData;

public class IfElseMetricChecker {
    public static void main(String[] origArgs) {
        Options opts = new Options();
        String[] args = Option.processCommandLine(origArgs, opts);

        Run.initClients();

        Registry.Factory<? extends Client> client;

        try {

            PrintStream console = System.out;

            // File file = new File(".temp");
            // FileOutputStream fos = new FileOutputStream(file);
            // PrintStream ps = new PrintStream(fos);
            // System.setOut(ps);

            Run.initGenerators(); // registers the available parsers
            String srcFile = "TestingData/ElseInsertion/a.py";
            String dstFile = "TestingData/ElseInsertion/b.py";
            // String srcFile = args[1];
            // String dstFile = args[2];
            Map<String, Integer> metrics = new Hashtable<>();
            Diff results = Diff.compute(srcFile, dstFile);
            // TreeClassifier classifier = results.createRootNodesClassifier();//we'll miss
            // a lot of changes if we just get root ndoes that changed
            TreeClassifier classifier = results.createAllNodeClassifier();
            PythonFileData fileData = PythonFileData.parseFile(srcFile, dstFile, 0, results, classifier);
            // Set<Tree> deletedSrcs = classifier.getDeletedSrcs();
            // TreeContext tc = TreeGenerators.getInstance().getTree(srcFile);
            // MetricRunner.dlog(tc);
            // for(Mapping m: results.mappings ){
            // MetricRunner.dlog(m.first + " \nmaps to:\n " + m.second);
            // }
            IfMetrics ifElseMetrics = new InsertedIfMetrics();
            ifElseMetrics.calc(metrics, results, classifier, fileData);
            MetricRunner.logAll(results.src.getRoot().toTreeString());
            for (Map.Entry<String, Integer> entry : metrics.entrySet()) {
                String key = entry.getKey();
                int val = entry.getValue();
                MetricRunner.dlog(key + " : " + val);
            }
        } catch (Exception e) {
            MetricRunner.dlog(e.toString());
        }
    }
}
